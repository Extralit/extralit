FROM python:3.10-slim AS builder

# Copying argilla distribution files
COPY dist/*.whl /packages/
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get install -y python-dev-is-python3 libpq-dev gcc && \
  pip install --upgrade uv && \
  uv pip install uvicorn[standard] && \
  for wheel in /packages/*.whl; do uv pip install "$wheel"[server,postgresql]; done && \
  apt-get remove -y python-dev-is-python3 libpq-dev gcc && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/* && \
  rm -rf /packages

FROM python:3.10-slim

RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get install -y libpq-dev nano && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Set environment variables for the container
# Environment Variables
ARG ENV=dev
ARG USERS_DB=/config/users.yaml
ENV ENV=$ENV

ENV USERNAME="argilla"
ENV PASSWORD="12345678"
ENV API_KEY="argilla.apikey"

## Argilla home path
ENV ARGILLA_HOME_PATH=/var/lib/argilla
ENV ARGILLA_LOCAL_AUTH_USERS_DB_FILE=$USERS_DB
## Uvicorn defaults
ENV UVICORN_PORT=6900
### Uvicorn app. Extended apps can override this variable
ENV UVICORN_APP=argilla_server:app


# Create a user and a volume for argilla
RUN useradd -ms /bin/bash argilla
RUN mkdir -p "$ARGILLA_HOME_PATH" && chown argilla:argilla "$ARGILLA_HOME_PATH"

# Copy the scripts and install uvicorn
COPY docker/server/scripts/ /home/argilla/

# Copy the entire repository into /home/argilla in the container
COPY . /home/argilla/

# Change the ownership of the /home/argilla directory to the new user
WORKDIR /home/argilla/

# Set up a virtual environment in /opt/venv
SHELL ["/bin/bash", "-c"]
RUN source /opt/venv/bin/activate
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
ENV UVICORN_APP=argilla_server:app

RUN uv pip install -q uvicorn[standard] -e "."
  
RUN chmod +x /home/argilla/start_argilla_server.sh && \
  chown -R argilla:argilla /home/argilla

# Switch to the argilla user
USER argilla

# Expose the necessary port
EXPOSE 6900

# Set the command for the container
CMD /bin/bash -c "/bin/bash start_argilla_server.sh"
