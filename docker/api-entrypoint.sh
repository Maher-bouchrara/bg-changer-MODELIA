#!/bin/sh
# Start of the API container.
#
#   no arguments   -> make sure the model is there, then start the web API
#   arguments      -> run them instead, e.g. the CLI:
#                     docker compose run --rm api bgchange /work/photo.jpg --color "#FF0066"
set -e

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# The weights live in the mounted models/ folder. Download them only if missing,
# so a computer that already has them (the developer's) downloads nothing.
if [ ! -f "$BGCHANGE_MODELS_DIR/$BGCHANGE_MODEL/model.safetensors" ]; then
    echo "Model '$BGCHANGE_MODEL' not found in $BGCHANGE_MODELS_DIR: downloading it once..."
    python scripts/download_models.py "$BGCHANGE_MODEL"
fi

# 0.0.0.0: reachable from outside the container (the port is published by compose).
exec bgchange-api --host 0.0.0.0 --port 8000
