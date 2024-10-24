#!/bin/bash

# Prune Docker builder cache
docker builder prune -af
docker image prune -af