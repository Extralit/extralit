#!/usr/bin/bash
set -e

# Set environment variables
if [ -z "$ARGILLA_ELASTICSEARCH" ] && [ -n "$ARGILLA_ELASTICSEARCH_HOST" ]; then
	echo 'Setting ARGILLA_ELASTICSEARCH with $ARGILLA_ELASTICSEARCH_PROTOCOL://elastic:$ARGILLA_ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST'
	export ARGILLA_ELASTICSEARCH=$ARGILLA_ELASTICSEARCH_PROTOCOL://elastic:$ARGILLA_ELASTIC_PASSWORD@$ARGILLA_ELASTICSEARCH_HOST
fi

if [ -z "$ARGILLA_DATABASE_URL" ] && [ -n "$POSTGRES_PASSWORD" ] && [ -n "$POSTGRES_HOST" ]; then
	echo 'Setting ARGILLA_DATABASE_URL with postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres'
	export ARGILLA_DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres
fi

# Run database migrations
python -m argilla_server database migrate

if [ -n "$USERNAME" ] && [ -n "$PASSWORD" ]; then
  echo "Creating owner user with username ${USERNAME}"

  cmd_args="--first-name $USERNAME --username $USERNAME --password $PASSWORD --role owner"

  if [ -n "$API_KEY" ]; then
    cmd_args="$cmd_args --api-key $API_KEY"
  fi

  if [ -n "$WORKSPACE" ]; then
    cmd_args="$cmd_args --workspace $WORKSPACE"
  fi

  python -m argilla_server database users create $cmd_args

else
  echo "No username and password was provided. Skipping user creation"
fi

# Reindexing data into search engine
index_count=$(python -m argilla_server search-engine list | wc -l)
if [ "$REINDEX_DATASETS" == "true" ] || [ "$REINDEX_DATASETS" == "1" ] || [ "$index_count" -le 1 ]; then
  echo "Reindexing existing datasets"
  python -m argilla_server search-engine reindex
fi

# Run argilla-server (See https://www.uvicorn.org/settings/#settings)
#
# From uvicorn docs:
#   You can also configure Uvicorn using environment variables
#   with the prefix UVICORN_. For example, in case you want to
#   run the app on port 5000, just set the environment variable
#   UVICORN_PORT to 5000.

if [ "$ENV" = "dev" ]; then
  echo 'Running in development mode'
  uvicorn $UVICORN_APP --host 0.0.0.0 --port $UVICORN_PORT --workers 4 --timeout-keep-alive 75 --reload
else
  uvicorn $UVICORN_APP --host 0.0.0.0 --port $UVICORN_PORT
fi