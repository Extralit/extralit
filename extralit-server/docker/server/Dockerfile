FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    MAMBA_ROOT_PREFIX=/opt/venv \
    CONDA_PREFIX=/opt/venv \
    UV_CACHE_DIR=/root/.cache/uv \
    # Pay for the .pyc files once here instead of on every worker's first import.
    UV_COMPILE_BYTECODE=1 \
    # The cache mount is a different filesystem from /opt/venv, so hardlinking cannot work.
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

# psycopg2 is built from source. The toolchain stays in this stage — the runtime image copies
# nothing out of it but the venv, so there is nothing to purge afterwards.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libc6-dev libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# --seed: the HF-Space image derives from this one and installs into this venv with `pip`.
RUN uv venv --seed "$VIRTUAL_ENV"

# Copied last: the wheel is the only input that differs between two builds of the same tree,
# so everything above it survives in the layer cache.
COPY dist/*.whl /packages/
RUN --mount=type=cache,target=/root/.cache/uv \
    for wheel in /packages/*.whl; do uv pip install "$wheel"[postgresql]; done

FROM python:3.12-slim

# Environment Variables
ENV USERNAME=""
ENV PASSWORD=""
ENV API_KEY=""
## Extralit home path
ENV EXTRALIT_HOME_PATH=/var/lib/extralit
## Uvicorn defaults
ENV UVICORN_PORT=6900
### Uvicorn app. Extended apps can override this variable
ENV UVICORN_APP=extralit_server:app

RUN useradd -ms /bin/bash extralit

# Create extralit volume
RUN mkdir -p "$EXTRALIT_HOME_PATH" && \
    chown extralit:extralit "$EXTRALIT_HOME_PATH" && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq-dev libgl1 libglib2.0-0 poppler-utils tesseract-ocr-eng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
VOLUME $EXTRALIT_HOME_PATH

# liteparse would otherwise download the language data on the first scanned page it meets.
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

COPY --chmod=0755 scripts/start_extralit_server.sh scripts/smoke_retrieval_deps.py scripts/install_lance_extension.py /home/extralit/
# Destination folder must be the same as the builder one. Otherwise installed script won't work (since the installation fixes the path inside the script)
COPY --chown=extralit:extralit --from=builder /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv

WORKDIR /home/extralit

USER extralit

# DuckDB resolves extensions per user home, so this runs as `extralit`: a hybrid search must
# not be the thing that discovers the runtime has no network.
RUN python install_lance_extension.py

# Exposing ports
EXPOSE 6900

CMD ["/bin/bash", "start_extralit_server.sh"]
