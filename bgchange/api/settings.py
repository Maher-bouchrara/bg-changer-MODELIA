"""The API's options, read from environment variables.

Environment variables (not a config file) because that is how Docker passes
options to a container (step 10). Every option has a sensible default, so
nothing needs to be set to run it locally.

    BGCHANGE_MODEL          which AI model to use            default: birefnet
    BGCHANGE_DEVICE         auto, cuda or cpu                default: auto
    BGCHANGE_MAX_UPLOAD_MB  biggest accepted upload          default: 20
    BGCHANGE_CORS_ORIGINS   web pages allowed to call it,    default: http://localhost:3000
                            comma-separated                  (the Next.js page in dev)
    BGCHANGE_PRELOAD        load the model at start-up       default: 1 (yes)
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from bgchange.s3_ai_models import DEFAULT_MODEL


@dataclass(frozen=True)
class Settings:
    model: str
    device: str
    max_upload_bytes: int
    cors_origins: list[str]
    preload: bool


def load_settings() -> Settings:
    """Read the environment variables now (called once, when the app is created)."""
    origins = os.environ.get("BGCHANGE_CORS_ORIGINS", "http://localhost:3000")
    return Settings(
        model=os.environ.get("BGCHANGE_MODEL", DEFAULT_MODEL),
        device=os.environ.get("BGCHANGE_DEVICE", "auto"),
        max_upload_bytes=int(float(os.environ.get("BGCHANGE_MAX_UPLOAD_MB", "20")) * 1024 * 1024),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        preload=os.environ.get("BGCHANGE_PRELOAD", "1") != "0",
    )
