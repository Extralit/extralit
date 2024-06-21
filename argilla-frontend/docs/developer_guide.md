# Developer Handoff
<details>
<summary>Click to expand</summary>

## Setup and Configuration
Step-by-step instructions for setting up and configuring the end-to-end solution.

The extralit system contain multiple microservices for managing the data storage, web servers and other processing services. The list of key components are:

- argilla-server: Contains the argilla web interface for data correction coupled with extralit server for data extraction services. This service is the main entry point for the data extraction pipeline.
- Postgres database: The main database for storing the extracted data and user accounts for the argilla-server.
- Elasticsearch: The search engine for the argilla-server to search and filter the data records.
- Minio: The file blob storage for storing the schemas, PDFs and intermediate model outputs.
- Weaviate: The vector database for storing the text and table sections in the paper.
- Langfuse: The LLM instrumentation service to trace and log the user's LLM data extraction queries.


### Install the Pre-requisites
These steps are required to set up infrastructure.

1. Install [Docker Desktop](https://docs.docker.com/get-docker/)
2. Install [Tilt](https://docs.tilt.dev/)

	This tools helps to manage the development environment and deploy services to Kubernetes by providing a single command to build, deploy, and monitor services. It automatically handles building, tagging, pushing, and pulling Docker images, along with live-updating for faster iterative development. It also provides a web interface to view logs of services and sets up port-forwarding to access the services from your workstation.
	
3. Install [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
4. Clone the `extralit-server` repository, checkout the `v0.2.0` tag, and build the python package and the frontend webserver: 

```bash
# Ensure you have git client version >= v2.45.1
git clone --recurse-submodules https://github.com/extralit/extralit-server
cd extralit-server
git fetch --tags
git checkout tags/v0.2.0
sh scripts/build_distribution.sh
```
5. Setup the Kubernetes cluster
<details>
<summary>Setting up a Local `kind` Kubernetes Cluster for development</summary>

If setting up a local Kubernetes cluster, you will need to install:

- Install [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- Install [ctlptl](https://github.com/tilt-dev/ctlptl/tree/main#how-do-i-install-it)

Then, create a `kind` cluster and set up the local docker registry

```bash
ctlptl create registry ctlptl-registry --port=5005
ctlptl create cluster {cluster_name} --registry=ctlptl-registry
```

Apply these config to mount a local directory to the kind cluster for storage persistence of the postgres, elasticsearch, minio, and weaviate services. This replaces the hard-coded storage class `k8s-storage-policy` in the various .yaml files to use the local storage. You should change the `/tmp/kind-volumes/` path specified in the `k8s/kind/kind-config.yaml` file, and `mkdir` and `chmod` with proper permissions to allow the `kind` cluster to mount the directory. 

```bash
# In the extralit-server repository root directory
ctlptl apply -f k8s/kind/kind-config.yaml
kubectl --context kind-kind taint node kind-control-plane node-role.kubernetes.io/control-plane:NoSchedule-
```

> :information_source: **INFO:** When using the kind cluster context, Tilt will automatically apply the `k8s/kind/tilt-local-dev-kind-storage-policy.yaml` which creates a `k8s-storage-policy` storage class in the Kind cluster to store data mounted in local storage. All the K8s yaml files were hard coded with the `k8s-storage-policy` storage class.
</details>

Import your Kubeconfig credentials from VMWare K8s deployment `{cluster_context}` in the `LLM Project`.

Select the K8s cluster
```bash
kubectl config set-cluster {cluster_name}
kubectl config use-context {cluster_context}
```

### Setting up services on the Kubernetes Cluster and setup the development tools

Environment variables for Tilt to deploy the services on the Kubernetes cluster:
- `ENV`: Set to `dev` for local development and `prod` for production deployment. When `ENV=dev`, the services will be hot-reloaded with code changes in the `extralit-server` repository.
- `NAMESPACE`: The Kubernetes namespace to deploy *all* the services.
- `DOCKER_REPO`: The Docker repository url to push the images to and for pods to pull images from. Set `localhost:5005` if deployed locally to kind cluster.
- `CLUSTER_CONTEXT`: The Kubernetes cluster context to deploy the services, e.g. `{cluster_context}`.

1. Create a new namespace if it doesn't exist

```bash
kubectl create ns {NAMESPACE}
```

2. Configure the services in the `k8s/` directory and setup the secrets. 

Review the [Tiltfile](https://github.com/extralit/extralit-server/blob/main/Tiltfile) for the services and their dependencies. 

Set up the secrets containing API keys and other variables, which are required by certain services. The secrets are used to store the database credentials, API keys, and other sensitive information.

```bash
# From this repo's root directory
kubectl apply -f extralit-secrets.yaml -n {NAMESPACE}
kubectl apply -f langfuse-secrets.yaml -n {NAMESPACE}
kubectl apply -f weaviate-api-keys.yaml -n {NAMESPACE}
```

3. Start K8s deployment with Tilt and deploy the services. You will need to configure the services according to your specific cluster setup. The namespace JT deployed on was `argilla-dev`, the cluster context was `{cluster_context}`, and the `ENV` was set to `dev` to enable live-reload of the servers.

```bash
# At extralit-server repository root directory
ENV={ENV} DOCKER_REPO={DOCKER_REPO} tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT}
```

<details>
<summary>:warning: If you're deploying on a local kind cluster, there might be issues with PVs</summary>

Due to the issue with PVC not matching with PVs, you may need to iteratively enable certain services in order to deploy, before running `tilt up` for all services. 

```bash
ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} elasticsearch
ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} main-db
ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} minio
ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT} weaviate

ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace {NAMESPACE} --context {CLUSTER_CONTEXT}
```
</details>



Go to `localhost:10350` to view the Tilt web interface. While tilt is running, any changes to `extralit-server` code, e.g. k8s yamls, helm values, and source code, will be automatically detected and the services will be reloaded. This is useful for development and debugging, but can be problematic when you are pulling changes from the repository, causing many services to rebuild unnecessarily. In that case, you can stop the Tilt process and restart it.


4. Set up user accounts: 

On a fresh install, the [start_argilla_server.sh](https://github.com/extralit/extralit-server/blob/main/docker/server/scripts/start_argilla_server.sh) script runs to create the Postgres database and user accounts, and migrations to set up the database schema. Importantly, it defines the `ARGILLA_DATABASE_URL` envvar and other envvars from K8s yaml configs that the Argilla server uses to connect to the database. The `argilla_server` CLI need these envvars to create user accounts, or reindex the ElasticSearch services (when needed).

User credentials are stored in the [users.yml](config/users.yaml) file in the `config` directory. The `argilla_server` CLI tool can be used is used to manage user accounts and permissions.

```bash
ARGILLA_DATABASE_URL=postgresql+asyncpg://postgres:$POSTGRES_PASSWORD@$POSTGRES_HOST/postgres \
ARGILLA_LOCAL_AUTH_USERS_DB_FILE=path/to/users.yaml \
argilla_server database users migrate
```

5. Run the [argilla web frontend](https://github.com/extralit/extralit) locally. 

First, check the public IP of the `argilla-server` service on K8s and set the `API_BASE_URL` environment variable to the IP address. Then, run the frontend server.

```bash
# At extralit-server repository root directory
cd argilla/argilla-frontend
npm install
API_BASE_URL=http://path.to.server npm run dev
```

6. Update the frontend webserver with the latest changes.

Access the Argilla web interface at `localhost:3000` with live-reloaded code changes.
When you want to update changes of the front-end webserver, run
```bash
# At extralit-server repository root directory
sh scripts/build_frontend.sh # builds the latest changes to `src/argilla_server/static` and optionally run unit tests
```

Finally, trigger a rebuild of the `argilla-server-deployment` resource with the ↻ button in the Tilt web interface.

7. Update the backend webserver with the latest changes.

When you change the backend code at `src/argilla_server/` or `src/extralit/`, the changes are automatically live-updated to the docker container running the backend server when `ENV=dev`, which enables live reloading in the uvicorn servers serving the FastAPI apps. If you do not see the changes, you can manually trigger a rebuild of the `argilla-server-deployment` and `extralit-server` resource with the ↻ button in the Tilt web interface. 

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


## Future Development for the handoff team
The project is still in the alpha development version, with only core data extraction functionalities as working prototypes, many services not production-ready, and several missing features to make it an end-to-end platform. I would recommend the following areas for future development to address the Troubleshooting issues described above:

### Data persistence
- [ ] Minio data persistence: use a cloud storage service like AWS S3 to store the extracted data files, or deploy the more stable `minio-operator` with data backup functionalities.
- [ ] Weaviate vectordb data persistence: Configure backup providers at [weaviate-helm.yaml](https://github.com/extralit/extralit-server/blob/main/k8s/helm/weaviate-helm.yaml) for the Weaviate service to backup/restore the vector embeddings of the document segments.
- [ ] `main-db` Postgres data persistence: 
Currently data are manually backed up with snapshots stored at a [OneDrive folder](#) using TablePlus, and manually restored with `pg_restore path/to/backup.dump -U postgres -W -d postgres -h localhost -p 5432 --clean`. 
- [ ] `elasticsearch` data persistence: Since the data index can be easily regenerated, it is not a high priority to backup the data. However, it is recommended to reconfigure the [elasticsearch-helm.yaml](https://github.com/extralit/extralit-server/blob/main/k8s/helm/elasticsearch-helm.yaml) to fix the issue with the `elasticsearch-master-0` pod not being able to mount the data shards stored in persistent volume when the deployment is redeployed.

### Data storage configurations
- [ ] Storage size requirements: many services are currently configured with default storage sizes, which may not be sufficient for production use. Configure the storage sizes for the `main-db` Postgres, `elasticsearch`, `minio`, and `weaviate` services to meet the data storage requirements. There are potentially data loss issues when the PVs are resized, especially for the `elasticsearch` service.
- [ ] Custom k8s storage classes: Configure custom storage classes for the `main-db` Postgres, `elasticsearch`, `minio`, and `weaviate` services to ensure that persistent volumes use `k8s-storage-policy` when deployed on VMWare K8s. This is currently hard-coded in the .yaml files listed above, and JT will soon provide a more flexible way to configure the custom storage classes using [Tilt configs](https://docs.tilt.dev/tiltfile_config#examples) on extralit open-source.


### Data extraction pipeline
The data extraction pipeline is currently not fully automated, requiring manual steps required to move data between services by running the notebooks. The following features are missing to make the data extraction pipeline fully automated:
- [ ] Integrating with a reference manager (e.g. Mendeley) to generate a reference table and add PDFs the argilla-server database. There is no feature to do this automatically, or to update the reference table with new PDFs.
- [ ] PDF Preprocessing service: The PDFs are not automatically processed and the table structure extraction need to run computationally intensive algorithms. The `pdf-preprocessing` service is not yet implemented or integrated with the `argilla-server` service.
- [ ] Data movements to and from the Argilla records: The data extracted from the PDFs are not automatically moved to the Argilla records. The submited Argilla records for table correction at the PDF preprocessing step are not automatically moved to the Weaviate database.


### Unfinished features for extralit open-source
The items above are features which were originally planned for this project but were not develop due to time constraints. JT will be working on several solutions for an automated data pipeline or workflow orchestrator to manage the data extraction pipeline in incoming v0.3.0 version releases. The following features are deemed necessary for the project to be production-ready:
- [ ] Documentation site
- [ ] Workflow orchestrator and automated data extraction pipeline
- [ ] Reference manager integration
- [ ] PDF Preprocessing service
- [ ] Extralit command-line interface tool for data export
- [ ] Data extraction schema editor in the web interface
- [ ] Test coverage and Github Actions CI/CD pipeline

Please feel free to reach out to the [extralit open-source Slack channel](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ) for any questions, issues, or to collaborate on the development roadmap of the project.
</details>
