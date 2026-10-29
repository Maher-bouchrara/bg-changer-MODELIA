# The API image (CPU): the bgchange command and the web API, ready to run.
#
#   docker compose up                       starts the API (and the web page)
#   docker compose run --rm api bgchange …  runs the CLI inside the same image
#
# The model weights are NOT in the image: the project's models/ folder is
# mounted at /app/models (docker-compose.yml). If BiRefNet is missing there, the
# container downloads it on its first start (docker/api-entrypoint.sh).
#
# Layers go from "changes rarely" to "changes often", so editing our code only
# rebuilds the last small layer; PyTorch and the other packages are reused.

FROM python:3.12-slim

# uv, the same version that wrote uv.lock (it installs the packages below).
COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=300

WORKDIR /app

# 1. PyTorch for CPU. pyproject.toml takes torch from the CUDA 12.8 index (for the
#    GPU on the development laptop); that build pulls ~3 GB of NVIDIA libraries a
#    CPU container never uses. Same torch version as uv.lock, CPU build.
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-hashes --no-emit-project > /tmp/requirements.txt \
 && TORCH=$(sed -n 's/^torch==\([0-9.]*\).*/\1/p' /tmp/requirements.txt) \
 && VISION=$(sed -n 's/^torchvision==\([0-9.]*\).*/\1/p' /tmp/requirements.txt) \
 && uv pip install "torch==${TORCH}" "torchvision==${VISION}" --index-url https://download.pytorch.org/whl/cpu

# 2. Every other package, at the exact versions of uv.lock. --no-deps: the list is
#    already complete, and it keeps transparent-background's 24 unused
#    dependencies out (see the note in pyproject.toml).
RUN grep -v -E '^(torch|torchvision|triton|nvidia-)' /tmp/requirements.txt > /tmp/others.txt \
 && uv pip install --no-deps -r /tmp/others.txt

# 3. Our code (the only layer rebuilt when it changes).
COPY README.md ./
COPY bgchange ./bgchange
COPY scripts ./scripts
COPY docker/api-entrypoint.sh /usr/local/bin/api-entrypoint
RUN uv pip install --no-deps . && chmod +x /usr/local/bin/api-entrypoint

# Run as a normal user, not root. outputs/ is where the CLI saves by default.
RUN useradd --create-home --uid 1000 app && mkdir -p /app/models /app/outputs && chown -R app /app
USER app

ENV BGCHANGE_MODELS_DIR=/app/models \
    BGCHANGE_MODEL=birefnet \
    BGCHANGE_DEVICE=cpu \
    HF_HOME=/app/models/.hf-cache

EXPOSE 8000
ENTRYPOINT ["api-entrypoint"]
