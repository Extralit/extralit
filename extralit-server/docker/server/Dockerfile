FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/
# Copying extralit distribution files
COPY dist/*.whl /packages/
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv
ENV UV_CACHE_DIR=/home/extralit/.cache/uv

RUN --mount=type=cache,target=/home/extralit/.cache/uv \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libc6-dev libpq-dev gcc && \
    for wheel in /packages/*.whl; do uv pip install "$wheel"[postgresql]; done && \
    apt-get purge -y --auto-remove libc6-dev libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /packages

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

COPY scripts/start_extralit_server.sh scripts/smoke_retrieval_deps.py /home/extralit/
# Destination folder must be the same as the builder one. Otherwise installed script won't work (since the installation fixes the path inside the script)
COPY --chown=extralit:extralit --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv

WORKDIR /home/extralit
RUN chmod +x start_extralit_server.sh

USER extralit

# Pull the community `lance` extension now: DuckDB resolves it per user home, and a hybrid
# search must not be the thing that discovers the runtime has no network.
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL lance')"

# Exposing ports
EXPOSE 6900

CMD ["/bin/bash", "start_extralit_server.sh"]
