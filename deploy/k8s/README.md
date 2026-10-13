# Extralit Helm Chart

Deploys the Extralit server and RQ worker, with in-chart PostgreSQL and Redis and an
Elasticsearch cluster managed by the ECK operator. Each backend can be swapped for an external one.

## Prerequisites

- Kubernetes 1.23+, Helm 3.8+
- A default StorageClass (or set the `*.persistence.storageClass` values)
- The [ECK operator](https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-install-helm.html),
  unless `elasticsearch.useOperator=false`

```bash
helm repo add elastic https://helm.elastic.co
helm install elastic-operator elastic/eck-operator -n elastic-system --create-namespace
```

## Install

```bash
helm install extralit deploy/k8s
kubectl port-forward svc/extralit 6900
```

Extralit is then at http://localhost:6900 (user `extralit`, password `12345678`, API key
`extralit.apikey` — change these via `extralit.auth.*`).

For a minikube ingress: `minikube addons enable ingress`, then install with
`--set extralit.ingress.enabled=true` and map `extralit.local` to `minikube ip` in `/etc/hosts`.

## Common values

| Value | Default | Notes |
|---|---|---|
| `extralit.image.repository` / `tag` | `extralit/extralit-server` / appVersion | `extralitdev/extralit-server` for `main` builds |
| `extralit.authSecretKey` | generated | Kept across upgrades |
| `extralit.baseUrl` | `""` | Serve under a path prefix, e.g. `/extralit` |
| `extralit.persistence.*` | 2Gi RWO at `/var/lib/extralit` | Holds file storage and LanceDB; shared by server and worker |
| `storage.url`, `storage.s3.*` | file storage on the PVC | `s3://bucket` or `http(s)://host/bucket` for MinIO/R2 |
| `postgresql.enabled` / `externalDatabase.url` | `true` / `""` | External URL format `postgresql+asyncpg://user:pass@host:5432/db` |
| `elasticsearch.useOperator` / `externalElasticsearch.url` | `true` / `""` | |
| `redis.enabled` / `externalRedis.url` | `true` / `redis://localhost:6379/0` | |
| `extralit.extraEnv` | `[]` | Any other `EXTRALIT_*` setting |

## Tests

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest.git
helm unittest deploy/k8s
helm test extralit   # against a running release
```
