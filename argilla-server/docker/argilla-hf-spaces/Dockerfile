# syntax=docker/dockerfile:1.4
ARG ARGILLA_VERSION=latest
ARG ARGILLA_SERVER_IMAGE=extralitdev/argilla-server

# Base stage with common dependencies
FROM ${ARGILLA_SERVER_IMAGE}:${ARGILLA_VERSION} AS base
USER root

# Copy Argilla distribution files
COPY scripts/start.sh /home/argilla
COPY Procfile /home/argilla
COPY requirements.txt /packages/requirements.txt

# Install system dependencies, Elasticsearch, and Redis in as few layers as possible
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
    apt-transport-https \
    gnupg \
    wget \
    lsb-release \
    curl \
    jq \
    pwgen \
    ; \
    # Elasticsearch key and repo
    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elasticsearch-keyring.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/elasticsearch-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" > /etc/apt/sources.list.d/elastic-8.x.list; \
    # Redis key and repo
    wget -qO - https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg; \
    echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" > /etc/apt/sources.list.d/redis.list; \
    apt-get update; \
    # Install Elasticsearch and Redis
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    elasticsearch=8.17.0 \
    redis \
    ; \
    # Remove build tools and clean up
    apt-get purge -y --auto-remove wget gnupg lsb-release apt-transport-https; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Create data directory and set permissions
RUN mkdir -p /data && chown -R argilla:argilla /data \
    && chown -R argilla:argilla /usr/share/elasticsearch /etc/elasticsearch /var/lib/elasticsearch /var/log/elasticsearch \
    && chown argilla:argilla /etc/default/elasticsearch

# Install Python dependencies and utilities
RUN pip install --no-cache-dir -r /packages/requirements.txt \
    && chmod +x /home/argilla/start.sh /home/argilla/start_argilla_server.sh

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

CMD ["/bin/bash", "start.sh"]