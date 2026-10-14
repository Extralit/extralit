# Deploy with Kubernetes

The Helm chart in [`deploy/k8s`](https://github.com/extralit/extralit/tree/main/deploy/k8s) deploys:

- `extralit` server: web UI and API on port 6900
- `extralit-worker`: RQ worker for background jobs (PDF parsing, indexing)
- PostgreSQL: main database (in-chart StatefulSet, or external)
- Redis: job queue, persisted with AOF (in-chart Deployment, or external)
- Elasticsearch: search engine for records (managed by the ECK operator, or external)

Uploaded files and LanceDB indexes live under `EXTRALIT_HOME_PATH` on a PersistentVolumeClaim shared by the server and worker, unless you point `storage.url` at S3-compatible storage.

## Prerequisites

- Kubernetes 1.23+ with a default StorageClass
- [kubectl](https://kubernetes.io/docs/tasks/tools/) and [Helm](https://helm.sh/docs/intro/install/) 3.8+
- The [ECK operator](https://www.elastic.co/guide/en/cloud-on-k8s/current/k8s-install-helm.html), unless you use an external Elasticsearch

For a local cluster, [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) or [minikube](https://minikube.sigs.k8s.io/docs/start/) both work; give it at least 4 GB of memory.

## Install

1. Install the ECK operator:

    ```bash
    helm repo add elastic https://helm.elastic.co
    helm install elastic-operator elastic/eck-operator -n elastic-system --create-namespace
    ```

2. Clone the repository and install the chart:

    ```bash
    git clone https://github.com/extralit/extralit.git
    cd extralit
    helm install extralit deploy/k8s -n extralit --create-namespace
    ```

    The owner password, API key and PostgreSQL password are generated unless you set `extralit.auth.password`, `extralit.auth.apiKey` and `postgresql.auth.password`.

3. Wait for the pods to become ready. The server pod runs database migrations and creates the owner user on startup, so it takes a minute or two:

    ```bash
    kubectl -n extralit get pods -w
    ```

4. Open Extralit:

    ```bash
    kubectl -n extralit port-forward svc/extralit 6900
    ```

    Then go to http://localhost:6900 and log in as `extralit`. Get the password with:

    ```bash
    kubectl -n extralit get secret extralit-secrets -o jsonpath='{.data.password}' | base64 -d
    ```

5. Optionally, check the release with the bundled Helm test:

    ```bash
    helm test extralit -n extralit
    ```

## Configuration

Set values with `--set` or a values file (`helm install ... -f my-values.yaml`). See [`values.yaml`](https://github.com/extralit/extralit/blob/main/deploy/k8s/values.yaml) for all options.

| Value | Default | Notes |
|---|---|---|
| `extralit.image.repository` / `tag` | `extralit/extralit-server` / chart `appVersion` | Use `extralitdev/extralit-server` for builds from `main` |
| `extralit.auth.username` / `password` / `apiKey` / `workspace` | `extralit` / generated / generated / `default` | Owner user created on first install only |
| `extralit.authSecretKey` | generated | Kept across upgrades |
| `extralit.baseUrl` | `""` | Serve under a path prefix, e.g. `/extralit` |
| `extralit.persistence.*` | 2Gi `ReadWriteOnce` at `/var/lib/extralit` | With `ReadWriteOnce` the worker runs on the server's node and rollouts use `Recreate`; use `ReadWriteMany` to spread pods |
| `extralit.ingress.*` | disabled | `className`, `host`, `annotations`, `tls` |
| `extralit.hpa.*` | disabled | Needs `ReadWriteMany` persistence; the chart refuses to render it with `ReadWriteOnce` |
| `nodeSelector`, `tolerations` | none | Applied to server and worker pods |
| `extralit.extraEnv` | `[]` | Any other `EXTRALIT_*` [server setting](../reference/extralit-server/configuration.md) |
| `storage.url`, `storage.s3.*` | files on the PVC | `s3://bucket[/prefix]`, or `http(s)://host[:port]/bucket` for MinIO and R2 |
| `postgresql.enabled` / `externalDatabase.url` | `true` / `""` | External format: `postgresql+asyncpg://user:pass@host:5432/db` |
| `elasticsearch.useOperator` / `externalElasticsearch.url` | `true` / `""` | External format: `http://user:pass@host:9200` |
| `redis.enabled` / `externalRedis.url` | `true` / `redis://localhost:6379/0` | `redis.persistence.*` keeps queued jobs across restarts |

### Ingress

To expose Extralit through an ingress controller, e.g. on minikube:

```bash
minikube addons enable ingress
helm upgrade extralit deploy/k8s -n extralit --reuse-values \
  --set extralit.ingress.enabled=true \
  --set extralit.ingress.host=extralit.local
echo "$(minikube ip) extralit.local" | sudo tee -a /etc/hosts
```

### External services

To use managed services instead of the in-chart ones:

```yaml
postgresql:
  enabled: false
externalDatabase:
  url: postgresql+asyncpg://extralit:<password>@db.example.com:5432/extralit

elasticsearch:
  useOperator: false
externalElasticsearch:
  url: https://elastic:<password>@es.example.com:9200

redis:
  enabled: false
externalRedis:
  url: redis://redis.example.com:6379/0

storage:
  url: s3://my-bucket/extralit
  s3:
    accessKey: <access-key>
    secretKey: <secret-key>
    region: us-east-1
```

## Upgrade and uninstall

```bash
helm upgrade extralit deploy/k8s -n extralit --reuse-values
helm uninstall extralit -n extralit
```

`helm uninstall` keeps the PostgreSQL and Elasticsearch PVCs. Delete them with `kubectl -n extralit delete pvc -l app.kubernetes.io/instance=extralit` and `kubectl -n extralit delete pvc -l elasticsearch.k8s.elastic.co/cluster-name=extralit` if you no longer need the data.

## Troubleshooting

- **Server pod restarts during startup:** check `kubectl -n extralit logs deploy/extralit`. Migrations and user creation need PostgreSQL and Elasticsearch to be ready; the server retries until its startup probe gives up after 10 minutes.
- **Pods stuck in `Pending`:** usually a PVC that can't bind. Check `kubectl -n extralit get pvc` and set the `*.persistence.storageClass` values if the cluster has no default StorageClass. With a `ReadWriteOnce` volume the worker is placed on the server's node, so it stays `Pending` until the server is scheduled.
- **Elasticsearch never becomes healthy:** check `kubectl -n extralit get elasticsearch` and the operator logs with `kubectl -n elastic-system logs statefulset/elastic-operator`. A single-node cluster needs about 2 GB of memory.
- **Search index lost:** records are stored in PostgreSQL, so you can rebuild the index with `kubectl -n extralit exec deploy/extralit -- python -m extralit_server search-engine reindex`.
- **Changed `extralit.auth.*` after install:** the owner user is only created on first install, so changing these values afterwards updates the Secret but not the user's real credentials.
- **Changed `postgresql.auth.password` after install:** PostgreSQL only reads it when initializing an empty volume. Change the password inside the database as well, or delete the PostgreSQL PVC to start over.

For support, join the [Extralit Slack channel](https://join.slack.com/t/extralit/shared_invite/zt-3gw1ah8bl-AiVNrkIVYOL4yVGOxN8WFw).
