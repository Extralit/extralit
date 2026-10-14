---
description: Guide for end-to-end installation of the Extralit system.
---

# Extralit System Installation Guide

This guide will walk you through the process of setting up the Extralit system end-to-end.

## Prerequisites

Before you begin, ensure you have the following:

- Python 3.9 or later
- Docker (for containerized deployment)
- Kubernetes cluster (for scalable deployment)
- Access to a PostgreSQL database
- Access to an Elasticsearch instance
- MinIO or S3-compatible object storage (optional; defaults to local disk under `EXTRALIT_HOME_PATH/storage`)

## Docker Compose behind a reverse proxy

[`deploy/docker`](https://github.com/extralit/extralit/tree/main/deploy/docker) runs the server, an RQ worker, PostgreSQL, Elasticsearch and Redis behind nginx or Traefik at `http://localhost/extralit/`:

```bash
cd deploy/docker
cp example.env .env   # set EXTRALIT_PASSWORD, EXTRALIT_API_KEY and POSTGRES_PASSWORD
docker compose --profile nginx up -d --wait     # or: --profile traefik
```

Set `EXTRALIT_IMAGE` to choose the server image. Text-extraction jobs need `extralit_ocr`, which the `extralit-server` image does not include.
