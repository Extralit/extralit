#!/bin/bash

# Perform the pip editable install
if ! pip list | grep -q "extralit"; then
    echo "Installing required packages and editable installs..."
    pdm config use_uv true
    pdm config python.install_root /opt/conda/
    uv pip install -q "sentence-transformers<3.0.0" transformers "textdescriptives<3.0.0" \
        -e /workspaces/extralit/argilla-server/ && \
        uv pip install -q -e /workspaces/extralit/argilla/
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
