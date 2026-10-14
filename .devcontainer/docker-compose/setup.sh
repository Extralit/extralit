#!/bin/bash

# Perform the pip editable install
if ! pip list | grep -q "extralit"; then
    echo "Installing required packages and editable installs..."
    uv pip install -q "sentence-transformers<3.0.0" transformers "textdescriptives<3.0.0" \
        -e /workspaces/extralit/extralit-server/ && \
        uv pip install -q -e /workspaces/extralit/extralit/
else
    echo "Package 'extralit' is already installed. Skipping installation."
fi

echo "Setup script completed."
