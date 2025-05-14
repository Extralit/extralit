# Multi-stage build to reduce image size
ARG ARGILLA_VERSION=latest
ARG ARGILLA_SERVER_IMAGE=extralitdev/argilla-server

# Base stage with common dependencies
FROM ${ARGILLA_SERVER_IMAGE}:${ARGILLA_VERSION} AS base
USER root

# Copy Argilla distribution files
COPY scripts/start.sh /home/argilla
COPY Procfile /home/argilla
COPY requirements.txt /packages/requirements.txt

# Install apt dependencies - breaking up large installations
RUN apt-get update && \
    apt-get install -y --no-install-recommends apt-transport-https gnupg wget && \
    # Install Elasticsearch signing key
    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list && \
    # Install Redis signing key
    wget -qO - https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg && \
    apt-get install -y --no-install-recommends lsb-release && \
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create data directory
RUN mkdir /data

# Install Elasticsearch - separate step to manage memory usage
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends elasticsearch=8.15.0 && \
    chown -R argilla:argilla /usr/share/elasticsearch /etc/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch && \
    chown argilla:argilla /etc/default/elasticsearch && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Redis - separate step to avoid memory allocation issues
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends redis && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies and additional utilities
RUN pip install --no-cache-dir -r /packages/requirements.txt && \
    chmod +x /home/argilla/start.sh && \
    chmod +x /home/argilla/start_argilla_server.sh && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends curl jq pwgen && \
    apt-get remove -y wget gnupg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /packages && \
    # Give ownership of the data directory to the argilla user
    chown -R argilla:argilla /data

COPY config/elasticsearch.yml /etc/elasticsearch/elasticsearch.yml

USER argilla

# NOTE: We have not found documentation about ELASTIC_CONTAINER environment variable but it could be
# used to indicate that Elasticsearch is running in a container.
# It is used in official Elastic Dockerfiles so we are not removing it for now:
# https://github.com/search?q=repo%3Aelastic%2Fdockerfiles%20ELASTIC_CONTAINER&type=code
ENV ELASTIC_CONTAINER=true
ENV ES_JAVA_OPTS="-Xms1g -Xmx1g"

ENV ARGILLA_HOME_PATH=/data/argilla
ENV REINDEX_DATASETS=1

ENV ARGILLA_DATABASE_URL=""
ENV ARGILLA_S3_ENDPOINT=""
ENV ARGILLA_S3_ACCESS_KEY=""
ENV ARGILLA_S3_SECRET_KEY=""
ENV ARGILLA_EXTRALIT_URL=""

CMD ["/bin/bash", "start.sh"]