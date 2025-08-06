FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /bin/
# Copying argilla distribution files
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
## Argilla home path
ENV ARGILLA_HOME_PATH=/var/lib/argilla
## Uvicorn defaults
ENV UVICORN_PORT=6900
### Uvicorn app. Extended apps can override this variable
ENV UVICORN_APP=argilla_server:app

RUN useradd -ms /bin/bash argilla

# Create argilla volume
RUN mkdir -p "$ARGILLA_HOME_PATH" && \
    chown argilla:argilla "$ARGILLA_HOME_PATH" && \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends libpq-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /packages
VOLUME $ARGILLA_HOME_PATH

COPY scripts/start_argilla_server.sh /home/argilla
# Destination folder must be the same as the builder one. Otherwise installed script won't work (since the installation fixes the path inside the script)
COPY --chown=argilla:argilla --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"
ENV MAMBA_ROOT_PREFIX=/opt/venv
ENV CONDA_PREFIX=/opt/venv

WORKDIR /home/argilla
RUN chmod +x start_argilla_server.sh

USER argilla

# Exposing ports
EXPOSE 6900

CMD ["/bin/bash", "start_argilla_server.sh"]
