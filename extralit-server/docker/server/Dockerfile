FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/
# Copying extralit distribution files
COPY dist/*.whl /packages/
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv

RUN --mount=type=cache,target=/root/.cache/uv \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libc6-dev libpq-dev gcc && \
    for wheel in /packages/*.whl; do uv pip install "$wheel"[server,postgresql]; done && \
    apt-get purge -y --auto-remove libc6-dev libpq-dev gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /packages

FROM python:3.13-slim

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
    apt-get install -y --no-install-recommends libpq-dev libgl1 libglib2.0-0 poppler-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
VOLUME $EXTRALIT_HOME_PATH

COPY scripts/start_extralit_server.sh /home/extralit
# Destination folder must be the same as the builder one. Otherwise installed script won't work (since the installation fixes the path inside the script)
COPY --chown=extralit:extralit --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv

WORKDIR /home/extralit
RUN chmod +x start_extralit_server.sh

USER extralit

# Exposing ports
EXPOSE 6900

CMD ["/bin/bash", "start_extralit_server.sh"]
