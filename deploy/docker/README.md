# Docker Compose behind a reverse proxy

Runs the Extralit server, an RQ worker, PostgreSQL, Elasticsearch and Redis, served at
http://localhost/extralit/ through nginx or Traefik.

```bash
cd deploy/docker
cp example.env .env   # set EXTRALIT_PASSWORD, EXTRALIT_API_KEY and POSTGRES_PASSWORD
docker compose --profile nginx up -d --wait     # or: --profile traefik
```

Log in as `extralit` with `EXTRALIT_PASSWORD`. The Traefik dashboard is at http://127.0.0.1:8080.

- `EXTRALIT_IMAGE` picks the server image, e.g. `extralitdev/extralit-server:latest` for builds from `main`.
- To serve under another path, change `EXTRALIT_BASE_URL`, the healthcheck URL, and the proxy path in
  `nginx.conf` or the Traefik router rule.
- Text-extraction jobs on the `ocr` queue need `extralit_ocr`, which this image lacks, so they fail.
