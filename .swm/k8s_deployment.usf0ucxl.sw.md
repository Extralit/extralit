---
title: k8s_deployment
---
# Kubernetes Development Setup

## Overview

The Extralit system consists of multiple microservices:

- argilla-server: Web server for data annotation, dataset management, and extraction services
- extralit-server: API server for data extraction, PDF parsing, and schema generation
- Postgres database: Main database for extracted data and user accounts
- Elasticsearch: Search engine for data records
- Minio/S3: File storage for schemas, PDFs, and intermediate outputs
- Weaviate: Vector database for text and table sections
- Langfuse: LLM instrumentation service for query tracing and logging

## Setup and Configuration

1. Install required tools:

   - [kubectl](https://kubernetes.io/docs/tasks/tools/)
   - [Tilt](https://docs.tilt.dev/install.html)
   - [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) (for local clusters)

2. Create a local Kubernetes cluster:

   ```bash
   kind create cluster --name {cluster_name}
   ```

3. Clone the repository:

   ```bash
   git clone https://github.com/extralit/extralit.git
   cd extralit
   ```

4. Set up the Kubernetes cluster: <details> <summary>Local `kind` Cluster Setup</summary>

   Install additional tools:

   - [ctlptl](https://github.com/tilt-dev/ctlptl/tree/main#how-do-i-install-it)

   Create cluster and local registry:

   ```bash
   ctlptl create registry ctlptl-registry --port=5005
   ctlptl create cluster {cluster_name} --registry=ctlptl-registry
   ```

   Apply storage configurations:

   ```bash
   ctlptl apply -f k8s/kind/kind-config.yaml
   kubectl --context kind-kind taint node kind-control-plane node-role.kubernetes.io/control-plane:NoSchedule-
   ```

   > **Note:** Tilt will apply `k8s/kind/tilt-local-dev-kind-storage-policy.yaml` for local storage class.

   </details>

5. Configure cluster context:

   ```bash
   kubectl config set-cluster {cluster_name}
   kubectl config use-context {cluster_context}
   ```

### Deploying Services

Set environment variables:

- `ENV`: `dev` for development, `prod` for production
- `NAMESPACE`: Kubernetes namespace for services
- `DOCKER_REPO`: Docker repository URL
- `CLUSTER_CONTEXT`: Kubernetes cluster context

1. Create namespace:

   ```bash
   kubectl create ns {NAMESPACE}
   ```

2. Set up secrets:

   ```bash
   kubectl apply -f extralit-secrets.yaml -n {NAMESPACE}
   kubectl apply -f langfuse-secrets.yaml -n {NAMESPACE}
   kubectl apply -f weaviate-api-keys.yaml -n {NAMESPACE}
   ```

3. Deploy services:

   We use Tilt to manage the development environment and deploys services to Kubernetes by providing a single command to build, deploy, and monitor services.

   ```bash
   ENV={ENV} DOCKER_REPO={DOCKER_REPO} tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT}
   ```

   If you set `DOCKER_REPO`, Tilt will automatically handles building, tagging, pushing, and pulling Docker images.

   <details> <summary>Troubleshooting PV issues on local clusters</summary>

   Deploy services iteratively:

   ```bash
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} elasticsearch
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} main-db
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} minio
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} weaviate
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT}
   ```

   </details>

4. Monitor deployment in Tilt UI: `http://localhost:10350`

### User Account Setup

Run the `start_argilla_server.sh` script for initial setup. Manage users with `argilla_server` CLI:

```bash
ARGILLA_DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres \
ARGILLA_LOCAL_AUTH_USERS_DB_FILE=path/to/users.yaml \
argilla_server database users migrate
```

### Frontend Development

1. Set up and run frontend:

   ```bash
   cd argilla/argilla-frontend
   npm install
   API_BASE_URL=http://path.to.server npm run dev
   ```

2. Update frontend:

   ```bash
   sh scripts/build_frontend.sh
   ```

3. Rebuild `argilla-server-deployment` in Tilt UI

### Backend Development

Changes to `src/argilla_server/` or `src/extralit/` are automatically updated while running Tilt with `ENV=dev`. Manually rebuild if needed.

## Troubleshooting

### Persistent Volume & storage clases

The services are configured to use persistent volumes (PVs) to store data, such as the Postgres database, Elasticsearch data, Minio files, and Weaviate vector embeddings. The PVs are created with a storage class, which currently is hard-coded to `k8s-storage-policy`. The storage class is defined in the K8s yaml files for each service, such as `main-db`, `elasticsearch`, `minio`, and `weaviate`.

However these issues can arise:

- The PVs are not available when the services are deployed, causing the services to fail to start. This especially happens on the `kind` cluster, the PV were not created automatically before the service is deployed, so the `k8s/kind/tilt-local-dev-kind-storage-policy.yaml` file has to manually create the PV.
- Some Persistent Volume Claim (PVC) may bound to the incorrect PV, depending on the order they were created, causing issues where the expected storage path doesn't match requirements of the . You may check the `uncategorized` resource under `unlabeled` in the Tilt web interface to see if the PVs were created, or restart this resource to recreate the PVs, but it doesn't always fix it. Sometimes `rm -rf /tmp/kind-volumes/` and restarting the `kind` cluster is needed for redeployment of elasticsearch and postgres.
- Many of the Persistent Volume definitions were initially setup with a modest size, 4Gi to 9Gi. This will need to be resized to support higher data storage requirements.

### Deployment

Check the Tilt web interface for services that are not green in deployment status. Services that often fail to deploy when the cluster restarts or the pods are restarted are:

- `elasticsearch`: This helm chart often fails to redeploy due to the `elasticsearch-master-0` worker pod not being able reach green status due to issues with the data-shards in the persistent volume when the deployment restart. This can be fixed by deleting the `elasticsearch-master-0` pod, the `elasticsearch-master-elasticsearch-master-0` PVC and PV and allowing it to recreate a new database.
- `main-db` Postgres: This service can fail to redeploy due to the `main-db-0` pod not being able to mount the original persistent volume when the helm chart is redeployed, because it generated a new random password that was different from the original password. Fix it by changing the `posgres-password` to original password in the `main-db` K8s secret.

### Data persistence

- `elasticsearch`: Same issue described above causes the data index to be lost when the `elasticsearch-master-0` pod is recreated. The data index can be restored with persistent data in the `main-db` Postgres database by reindexing the data with the `argilla_server` CLI tool, see [check_search_engine.sh](https://github.com/extralit/extralit-server/blob/main/docker/server/scripts/check_search_engine.sh).
- `minio`: As a standalone pod in the K8s cluster for file blob storage, the Minio service is not automatically backed up. The data in the Minio bucket can be lost if the pod is deleted or the cluster fails in anyway. The data can be restored by re-uploading the data to the Minio bucket.

For support, join the [Extralit Slack channel](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ).

<SwmMeta version="3.0.0"><sup>Powered by [Swimm](https://app.swimm.io/)</sup></SwmMeta>
