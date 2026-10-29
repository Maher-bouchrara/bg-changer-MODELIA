"""The `bgchange-api` command: start the web API.

    uv run bgchange-api                          # http://127.0.0.1:8000, docs at /docs
    uv run bgchange-api --port 9000
    uv run bgchange-api --host 0.0.0.0           # reachable from other machines / Docker
    uv run bgchange-api --model ben2

Other options are environment variables, see settings.py.
"""

from __future__ import annotations

import argparse
import os

from bgchange.s3_ai_models import MODELS


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="bgchange-api", description="Start the bgchange web API.")
    parser.add_argument("--host", default="127.0.0.1", help="default: 127.0.0.1 (this computer only)")
    parser.add_argument("--port", type=int, default=8000, help="default: 8000")
    parser.add_argument("--model", choices=list(MODELS), help="AI model (default: BGCHANGE_MODEL or birefnet)")
    args = parser.parse_args(argv)

    if args.model:
        os.environ["BGCHANGE_MODEL"] = args.model  # read by settings.py when the app is created

    import uvicorn  # imported here so `bgchange-api --help` answers instantly

    uvicorn.run("bgchange.api.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
