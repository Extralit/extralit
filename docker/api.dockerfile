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
  apt-get update && \
  apt-get install -y python-dev-is-python3 libpq-dev gcc nano && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# Set up a virtual environment in /opt/venv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the scripts and install uvicorn
COPY docker/scripts/start_argilla_server.sh /home/argilla/


# Copy the entire repository into /home/argilla in the container
COPY . /home/argilla/

# Change the ownership of the /home/argilla directory to the new user
RUN chown -R argilla:argilla /home/argilla
WORKDIR /home/argilla/

RUN chmod +x /home/argilla/start_argilla_server.sh && \
  pip install -q uvicorn[standard] && \
  pip install -q -e ".[server,postgresql]"

# Conditionally run the command based on ENV
# RUN if [ "$ENV" = "dev" ]; then pip install --upgrade -e . ; fi

# Switch to the argilla user
USER argilla

# Expose the necessary port
EXPOSE 6900

RUN echo 'export ARGILLA_ELASTICSEARCH=https://elastic:$ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST' >> /home/argilla/.bashrc && \
  echo 'export ARGILLA_DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres' >> /home/argilla/.bashrc

# Set the command for the container
CMD /bin/bash -c "/bin/bash start_argilla_server.sh"
