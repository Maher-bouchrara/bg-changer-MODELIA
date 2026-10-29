"""create_app(): build the web API.

What happens when the server starts:

    1. read the settings (environment variables, settings.py)
    2. load the AI model ONCE, so every request is fast (~1-3 s instead of ~10 s)
       if the model is missing, the server still starts and /api/health says so
    3. allow the web page to call it (CORS: a browser blocks calls from one
       address, e.g. localhost:3000, to another, e.g. localhost:8000, unless the
       API says it is fine)
    4. turn every error into {"error": "..."} (one shape for the web page to read)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from bgchange import __version__, pipeline
from bgchange.api.routes import router
from bgchange.api.settings import Settings, load_settings
from bgchange.device import pick_device

log = logging.getLogger("bgchange.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # 2. Load the model once, before the first request.
        app.state.settings = settings
        app.state.device = str(pick_device(settings.device))
        app.state.model_loaded = False
        if settings.preload:
            try:
                await run_in_threadpool(pipeline.get_segmenter, settings.model, settings.device)
                app.state.model_loaded = True
                log.info("model %s loaded on %s", settings.model, app.state.device)
            except FileNotFoundError as error:
                log.error("%s", error)  # keep running: /api/health reports model_loaded = false
        yield

    app = FastAPI(
        title="bgchange API",
        version=__version__,
        description=(
            "Put the subject of a photo (person or product) on a new background colour, "
            "keeping a shadow. The same tool as the `bgchange` command."
        ),
        lifespan=lifespan,
    )

    # 3. Which web pages may call the API, and which response headers they may read.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Processing-Time-Ms", "X-Image-Size", "X-Model"],
    )

    # 4. One error shape: {"error": "..."}.
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's own check of the form (missing field, strength 2...) answers 422
        # with a long list; we answer 400 with the first problem in one sentence.
        first = exc.errors()[0]
        field = first["loc"][-1] if first.get("loc") else "request"
        return JSONResponse({"error": f"{field}: {first['msg']}"}, status_code=400)

    app.include_router(router)
    return app


#: The app uvicorn runs: `uvicorn bgchange.api.app:app` (or `uv run bgchange-api`).
app = create_app()
