#!/bin/bash

mkdir -p /tmp/k3d-volumes/elasticsearch /tmp/k3d-volumes/postgresql /tmp/k3d-volumes/minio /tmp/k3d-volumes/weaviate

# Create k3d cluster for local development with ctlptl and Tilt
if ! ctlptl get registry | grep -q "ctlptl-registry"; then
    ctlptl create registry ctlptl-registry --port=5005
else
    echo 'Registry ctlptl-registry already exists. Skipping creation.'
fi

# Set up cron job to prune Docker builder cache every 15 minutes to clean up disk space
(crontab -l 2>/dev/null; echo '*/15 * * * * /workspace/prune_docker.sh') | crontab -

# Perform the pip editable install
if ! pip list | grep -q "extralit"; then
    echo 'Installing required packages and editable installs...'
    uv pip install -e /workspaces/extralit/extralit-server/
    uv pip install -e /workspaces/extralit/extralit/
else
    echo 'Package 'extralit' is already installed. Skipping installation.'
fi

# Install precommit hooks
cd /workspaces/extralit
pre-commit install

echo 'Setup script completed'
