#!/usr/bin/env bash

if [ "$ENV" != "dev" ]; then
    cd frontend \
    && npm install \
    && BASE_URL=@@baseUrl@@ DIST_FOLDER=../src/argilla/server/static npm run-script build 
    # && npm run-script lint \
    # && npm run-script test
fi
