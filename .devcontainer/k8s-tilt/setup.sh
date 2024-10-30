#!/bin/bash

# Create k3d cluster for local development with ctlptl and Tilt
if ! ctlptl get registry | grep -q "ctlptl-registry"; then
    ctlptl create registry ctlptl-registry --port=5005
    ctlptl apply -f examples/deployments/k8s/k3d/k3d-config.yaml
else
    echo "Registry ctlptl-registry already exists. Skipping creation."
fi

# Set up cron job to prune Docker builder cache every 30minutes to clean up disk space
(crontab -l 2>/dev/null; echo "*/15 * * * * /workspace/prune_docker.sh") | crontab -

# Perform the pip editable install
if ! pip list | grep -q "extralit"; then
    echo "Installing required packages and editable installs..."
    uv pip install -e /workspaces/extralit/argilla-server/ && uv pip install -e /workspaces/extralit/argilla/ &
else
    echo "Package 'extralit' is already installed. Skipping installation."
fi

# Check if the upstream remote already exists
git config --global --add safe.directory /workspaces/extralit
if ! git remote get-url upstream &>/dev/null; then
    echo "Adding upstream remote..."
    git remote add upstream https://github.com/argilla-io/argilla
    git fetch upstream --no-tags
else
    echo "Upstream remote already exists. Skipping addition."
fi


echo "Setup script completed."
