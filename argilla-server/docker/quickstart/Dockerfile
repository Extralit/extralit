# TODO(gabrielmbmb): update this `Dockerfile` to multi-staged build to reduce the image size
ARG ARGILLA_VERSION=latest
FROM extralit/argilla-server:${ARGILLA_VERSION}

USER root

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    gnupg \
    wget

# Install Elasticsearch signing key
RUN wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg

# Add Elasticsearch repository
RUN echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list

# Copy Argilla distribution files
COPY scripts/start_quickstart_argilla.sh /home/argilla
COPY scripts/start_argilla_server.sh /home/argilla
COPY Procfile /home/argilla
COPY requirements.txt /packages/requirements.txt

RUN \
    # Indicate that this is a quickstart deployment
    echo -e "{  \"deployment\":  \"quickstart\" }" > /opt/venv/lib/python3.10/site-packages/argilla_server/static/deployment.json && \
    # Create a directory where Elasticsearch and Argilla will store their data
    mkdir /data && \
    # Install Elasticsearch and configure it
    apt-get update && apt-get install -y elasticsearch=8.15.0 && \
    chown -R argilla:argilla /usr/share/elasticsearch /etc/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch && \
    chown argilla:argilla /etc/default/elasticsearch && \
    # Install quickstart image dependencies
    pip install -r /packages/requirements.txt && \
    chmod +x /home/argilla/start_quickstart_argilla.sh && \
    chmod +x /home/argilla/start_argilla_server.sh && \
    # Give ownership of the data directory to the argilla user
    chown -R argilla:argilla /data && \
    # Clean up
    apt-get remove -y wget gnupg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /packages

COPY config/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

USER argilla

# NOTE: We have not found documentation about ELASTIC_CONTAINER environment variable but it could be
# used to indicate that Elasticsearch is running in a container.
# It is used in official Elastic Dockerfiles so we are not removing it for now:
# https://github.com/search?q=repo%3Aelastic%2Fdockerfiles%20ELASTIC_CONTAINER&type=code
ENV ELASTIC_CONTAINER=true
ENV ES_JAVA_OPTS="-Xms1g -Xmx1g"

ENV OWNER_USERNAME=""
ENV OWNER_PASSWORD=""
ENV OWNER_API_KEY=""

ENV ADMIN_USERNAME=""
ENV ADMIN_PASSWORD=""
ENV ADMIN_API_KEY=""

ENV ANNOTATOR_USERNAME=""
ENV ANNOTATOR_PASSWORD=""

ENV ARGILLA_HOME_PATH=/data/argilla
ENV ARGILLA_WORKSPACE=$ADMIN_USERNAME

ENV ARGILLA_DATABASE_URL=""
ENV S3_ENDPOINT=""
ENV S3_ACCESS_KEY=""
ENV S3_SECRET_KEY=""
ENV EXTRALIT_URL=""

ENV UVICORN_PORT=6900

ENV REINDEX_DATASETS=0

CMD ["/bin/bash", "start_quickstart_argilla.sh"]
