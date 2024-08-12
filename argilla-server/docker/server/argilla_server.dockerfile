# Use python:3.10.12-slim as the base image
FROM python:3.10.12-slim

COPY dist/*.whl /packages/

# Set environment variables for the container
ARG ENV=dev
ARG USERS_DB=/config/users.yaml
ENV ENV=$ENV
ENV ARGILLA_LOCAL_AUTH_USERS_DB_FILE=$USERS_DB
ENV ARGILLA_HOME_PATH=/var/lib/argilla
ENV DEFAULT_USER_ENABLED=true
ENV DEFAULT_USER_PASSWORD=1234
ENV DEFAULT_USER_API_KEY=argilla.apikey
ENV UVICORN_PORT=6900

# Create a user and a volume for argilla
RUN useradd -ms /bin/bash argilla
RUN mkdir -p "$ARGILLA_HOME_PATH" && \
  chown argilla:argilla "$ARGILLA_HOME_PATH" && \
  apt-get update -q && \
  apt-get install -q --no-install-recommends -y python-dev-is-python3 libpq-dev gcc nano && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Copy the scripts and install uvicorn
COPY docker/server/scripts/ /home/argilla/

# Copy the entire repository into /home/argilla in the container
COPY . /home/argilla/

# Change the ownership of the /home/argilla directory to the new user
WORKDIR /home/argilla/

# Set up a virtual environment in /opt/venv
SHELL ["/bin/bash", "-c"]
RUN pip install -q uv && uv venv /opt/venv && source /opt/venv/bin/activate
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

RUN uv pip install -q uvicorn[standard] -e ".[argilla_server,postgresql]"
  
RUN chmod +x /home/argilla/start_argilla_server.sh /home/argilla/check_search_engine.sh && \
  chown -R argilla:argilla /home/argilla

# Switch to the argilla user
USER argilla

# Expose the necessary port
EXPOSE 6900

# Set the command for the container
CMD /bin/bash -c "/bin/bash start_argilla_server.sh"





