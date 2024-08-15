#!/usr/bin/bash
set -e

# Set environment variables
if [ -z "$ARGILLA_ELASTICSEARCH" ] && [ -n "$ARGILLA_ELASTICSEARCH_HOST" ]; then
	echo 'Setting ARGILLA_ELASTICSEARCH with $ARGILLA_ELASTICSEARCH_PROTOCOL://elastic:$ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST'
	export ARGILLA_ELASTICSEARCH=$ARGILLA_ELASTICSEARCH_PROTOCOL://elastic:$ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST
fi

if [ -z "$ARGILLA_DATABASE_URL" ] && [ -n "$POSTGRES_PASSWORD" ] && [ -n "$POSTGRES_HOST" ]; then
	echo 'Setting ARGILLA_DATABASE_URL with postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres'
	export ARGILLA_DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres
fi

# Run database migrations
python -m argilla_server database migrate

# Create default user
if [ "$DEFAULT_USER_ENABLED" = "true" ]; then
	python -m argilla_server database users create_default --password $DEFAULT_USER_PASSWORD --api-key $DEFAULT_USER_API_KEY
fi

# Check search engine index
index_count=$(python -m argilla_server search-engine list | wc -l)
if [ "$index_count" -le 1 ] && { [ "$REINDEX_DATASETS" == "true" ] || [ "$REINDEX_DATASETS" == "1" ]; }; then
    python -m argilla_server search-engine reindex
fi

# Run argilla-server (See https://www.uvicorn.org/settings/#settings)
#
# From uvicorn docs:
#   You can also configure Uvicorn using environment variables
#   with the prefix UVICORN_. For example, in case you want to
#   run the app on port 5000, just set the environment variable
#   UVICORN_PORT to 5000.
python -m uvicorn argilla_server:app --host "0.0.0.0"
