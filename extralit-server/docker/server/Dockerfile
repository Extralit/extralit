# The duckdb the venv resolves. Pinned so the 231 MB extension fetch can sit in a stage that does
# not depend on the application wheel; the `--check` below fails the build if the pin ever drifts.
ARG DUCKDB_VERSION=1.5.5

# Fetched in its own stage, ahead of anything that changes per build: DuckDB looks extensions up
# under a version-named directory, so this layer is identical until duckdb itself moves.
FROM python:3.12-slim AS lance
ARG DUCKDB_VERSION
COPY scripts/install_lance_extension.py /tmp/
RUN python /tmp/install_lance_extension.py --duckdb-home /lance --duckdb-version "$DUCKDB_VERSION"

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.12.6 /uv /uvx /bin/

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
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

# The wheel is the only input that differs between two builds of the same tree, so it enters
# last — and as a bind mount, which leaves no copy of it behind in the stage.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=dist,target=/packages \
    for wheel in /packages/*.whl; do uv pip install "$wheel"[postgresql]; done

FROM python:3.12-slim
ARG DUCKDB_VERSION

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

# Layers below are ordered by how often they change, because a rebuilt layer rebuilds every layer
# under it. DuckDB resolves extensions per user home, hence extralit's rather than root's.
COPY --from=lance --chown=extralit:extralit /lance /home/extralit/.duckdb
COPY --chmod=0755 scripts/start_extralit_server.sh scripts/smoke_retrieval_deps.py scripts/install_lance_extension.py /home/extralit/
# Destination folder must be the same as the builder one. Otherwise installed script won't work (since the installation fixes the path inside the script)
COPY --chown=extralit:extralit --from=builder /opt/venv /opt/venv

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /home/extralit

USER extralit

# Fails the build rather than shipping an image whose first hybrid search cannot load the
# extension. Reads metadata only, so it survives the emulated arch of a release build.
RUN python install_lance_extension.py --check --duckdb-version "$DUCKDB_VERSION"

# Exposing ports
EXPOSE 6900

CMD ["/bin/bash", "start_extralit_server.sh"]
