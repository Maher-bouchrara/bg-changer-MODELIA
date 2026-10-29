"""Tests for bgchange/api/: the 2 routes, the error shape, the upload limit.

FastAPI's TestClient sends real HTTP requests to the app in memory (no server,
no network). The AI model is replaced by FakeModel, as in test_pipeline_and_cli.py.
"""

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

import bgchange.pipeline as pipeline
from bgchange.api.app import create_app
from bgchange.api.routes import ShadowKind
from bgchange.api.settings import Settings
from bgchange.s3_ai_models import Segmenter
from bgchange.s4_shadow import SHADOW_KINDS


class FakeModel(Segmenter):
    name = "fake"

    def predict(self, image):
        mask = np.zeros((image.height, image.width), np.float32)
        mask[image.height // 4 : 3 * image.height // 4, image.width // 4 : 3 * image.width // 4] = 1.0
        return mask


SETTINGS = Settings(
    model="birefnet", device="cpu", max_upload_bytes=200_000, cors_origins=["http://localhost:3000"], preload=True
)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(pipeline, "get_segmenter", lambda name, device: FakeModel())
    with TestClient(create_app(SETTINGS)) as c:  # "with" runs the start-up (model loading)
        yield c


def png_bytes(size=(80, 60), color=(200, 30, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def post(client, data=None, file=None, filename="shoe.png"):
    files = {"image": (filename, file if file is not None else png_bytes(), "image/png")}
    return client.post("/api/change-background", data=data or {"color": "#00FF00"}, files=files)


# --- GET /api/health -----------------------------------------------------------


def test_health_says_model_is_loaded(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model": "birefnet", "model_loaded": True, "device": "cpu"}


def test_health_reports_a_missing_model(monkeypatch):
    def missing(name, device):
        raise FileNotFoundError("Model 'birefnet' is not downloaded")

    monkeypatch.setattr(pipeline, "get_segmenter", missing)
    with TestClient(create_app(SETTINGS)) as c:  # the server still starts
        assert c.get("/api/health").json()["model_loaded"] is False
        response = post(c)
        assert response.status_code == 503
        assert "not downloaded" in response.json()["error"]


# --- POST /api/change-background --------------------------------------------------


def test_returns_the_png(client):
    response = post(client)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    image = Image.open(io.BytesIO(response.content))
    assert image.size == (80, 60)
    assert image.getpixel((0, 0)) == (0, 255, 0)  # corner = background = the new colour


def test_useful_headers(client):
    response = post(client, data={"color": "#FF0066"})
    assert response.headers["x-image-size"] == "80x60"
    assert response.headers["x-model"] == "birefnet"
    assert int(response.headers["x-processing-time-ms"]) >= 0
    assert 'filename="shoe_on_FF0066.png"' in response.headers["content-disposition"]


@pytest.mark.parametrize("shadow", SHADOW_KINDS)
def test_every_shadow_choice_works(client, shadow):
    assert post(client, data={"color": "#FFFFFF", "shadow": shadow, "shadow_strength": "0.5"}).status_code == 200


def test_api_and_pipeline_shadow_names_match():
    assert ShadowKind.__args__ == SHADOW_KINDS


def test_transparent_colour_gives_rgba(client):
    image = Image.open(io.BytesIO(post(client, data={"color": "#00000000"}).content))
    assert image.mode == "RGBA"


# --- Errors: always {"error": "..."} ------------------------------------------------


@pytest.mark.parametrize(
    ("data", "part"),
    [
        ({"color": "red"}, "not a hex colour"),
        ({"color": "#FFFFFF", "shadow": "soft"}, "shadow"),
        ({"color": "#FFFFFF", "shadow_strength": "2"}, "shadow_strength"),
        ({}, "color"),  # missing field
    ],
)
def test_bad_options_are_400(client, data, part):
    files = {"image": ("shoe.png", png_bytes(), "image/png")}
    response = client.post("/api/change-background", data=data, files=files)
    assert response.status_code == 400
    assert part in response.json()["error"]


def test_not_an_image_is_415(client):
    response = post(client, file=b"this is not an image", filename="notes.txt")
    assert response.status_code == 415
    assert "error" in response.json()


def test_too_large_is_413(client):
    response = post(client, file=b"0" * 200_001)
    assert response.status_code == 413
    assert "MB" in response.json()["error"]


def test_web_page_is_allowed_to_call_it(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_interactive_docs_exist(client):
    assert client.get("/docs").status_code == 200
    assert "/api/change-background" in client.get("/openapi.json").json()["paths"]
