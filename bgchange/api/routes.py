"""The 2 routes of the API.

    GET  /api/health
        -> {"status": "ok", "model": "birefnet", "model_loaded": true, "device": "cuda"}

    POST /api/change-background      (a form with a file, like any web upload)
        image            the photo                       required
        color            "#FF0066"                       one of these two:
        background       a picture to put behind it      a colour OR a picture
        shadow           real | fake | mix | none        default: real
        shadow_strength  0 to 1                          default: 1
        -> the PNG itself (Content-Type: image/png)

Errors are always {"error": "a sentence for people"} with:

    400  bad colour or option, a missing field, or both / neither of color and background
    413  a file is bigger than the upload limit (20 MB by default)
    415  the file is not an image we can read
    503  the model is not downloaded on the server
"""

from __future__ import annotations

import io
import re
import threading
import time
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel

from bgchange import pipeline
from bgchange.s1_load_photo import ImageLoadError
from bgchange.s2_read_color import ColorParseError

router = APIRouter(prefix="/api")

# One photo at a time on the GPU: two at once could run out of graphics memory,
# and would not be faster (they would share the same GPU). Other requests wait.
_gpu_lock = threading.Lock()

ShadowKind = Literal["real", "fake", "mix", "none"]  # same names as s4_shadow.SHADOW_KINDS


class Health(BaseModel):
    status: str
    model: str
    model_loaded: bool
    device: str


@router.get("/health", summary="Is the server up, and is the model loaded?")
def health(request: Request) -> Health:
    state = request.app.state
    return Health(status="ok", model=state.settings.model, model_loaded=state.model_loaded, device=state.device)


@router.post(
    "/change-background",
    summary="Put the subject of a photo on a new background colour or picture",
    response_class=Response,
    responses={
        200: {"content": {"image/png": {}}, "description": "The result as a PNG"},
        400: {"description": "Bad colour or option"},
        413: {"description": "File too large"},
        415: {"description": "Not a readable image"},
        503: {"description": "Model not downloaded on the server"},
    },
)
async def change_background(
    request: Request,
    image: Annotated[UploadFile, File(description="The photo: JPEG, PNG, WebP...")],
    color: Annotated[
        str | None, Form(description="New background as hex: #RGB, #RRGGBB or #RRGGBBAA", examples=["#FF0066"])
    ] = None,
    background: Annotated[
        UploadFile | None, File(description="Or a picture to put behind the subject, instead of a colour")
    ] = None,
    shadow: Annotated[ShadowKind, Form(description="real = the photo's own shadow, fake, mix or none")] = "real",
    shadow_strength: Annotated[float, Form(ge=0.0, le=1.0, description="0 = no shadow, 1 = as computed")] = 1.0,
) -> Response:
    settings = request.app.state.settings
    # Browsers send an empty file field when no file was chosen: same as no field.
    if background is not None and not background.filename:
        background = None
    color = color.strip() if color and color.strip() else None
    if (color is None) == (background is None):
        raise HTTPException(400, "Send exactly one background: a colour (color) or a picture (background).")

    data = await _read_limited(image, settings.max_upload_bytes)
    background_data = await _read_limited(background, settings.max_upload_bytes) if background else None

    start = time.perf_counter()
    # The AI work blocks for a second or two: run it in a worker thread so the
    # server keeps answering other requests (e.g. /api/health) meanwhile.
    result = await run_in_threadpool(_run, data, color, background_data, shadow, shadow_strength, settings)
    png = _to_png(result.image)
    elapsed_ms = round((time.perf_counter() - start) * 1000)

    on = result.color.to_hex().lstrip("#") if result.color else _safe_stem(background.filename)
    name = f"{_safe_stem(image.filename)}_on_{on}.png"
    return Response(
        png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{name}"',
            "X-Processing-Time-Ms": str(elapsed_ms),
            "X-Image-Size": f"{result.image.width}x{result.image.height}",
            "X-Model": settings.model,
        },
    )


async def _read_limited(upload: UploadFile, limit: int) -> bytes:
    """The uploaded file's bytes, or 413. Reads at most one byte more than the
    limit: enough to know it is too big, without loading a huge file into memory."""
    data = await upload.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"The file is larger than {limit // (1024 * 1024)} MB.")
    return data


def _run(
    data: bytes, color: str | None, background: bytes | None, shadow: str, strength: float, settings
) -> pipeline.Result:
    """Call the shared pipeline and turn its errors into HTTP errors."""
    try:
        with _gpu_lock:
            return pipeline.change_background(
                data,
                color,
                background_image=background,
                model=settings.model,
                shadow=shadow,
                shadow_strength=strength,
                device=settings.device,
            )
    except ColorParseError as error:
        raise HTTPException(400, str(error)) from None
    except ImageLoadError as error:
        raise HTTPException(415, str(error)) from None
    except FileNotFoundError as error:  # model weights missing on the server
        raise HTTPException(503, str(error)) from None


def _to_png(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _safe_stem(filename: str | None) -> str:
    """The upload's name without extension, keeping only safe characters for a file name."""
    stem = (filename or "").rsplit(".", 1)[0]
    return re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-")[:60] or "image"
