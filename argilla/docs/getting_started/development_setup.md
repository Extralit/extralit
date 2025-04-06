---
description: Comprehensive setup instructions for Extralit development
---

# Development Setup

This guide provides detailed instructions for setting up the Extralit development environment using different approaches, from beginner-friendly options to advanced configurations.

## Option 1: GitHub Codespaces (Recommended for Beginners)

GitHub Codespaces provides a fully configured development environment with all necessary tools pre-installed, making it the easiest way to get started.

### 1. Setting Up a Codespace

There are two ways to create a Codespace for the Extralit project:

#### Method A: From Your Fork
1. Fork the [Extralit repository](https://github.com/extralit/extralit) to your GitHub account
2. Navigate to your forked repository
3. Click the "Code" button
4. Select the "Codespaces" tab
5. Click "Create codespace on develop" to launch a new development environment

#### Method B: Using Existing Repository
1. Go to [GitHub Codespaces](https://github.com/codespaces)
2. Click "New codespace"
3. Select the Extralit repository or enter the repository URL
4. Choose the branch (typically "develop")
5. Select your preferred machine type
6. Click "Create codespace"

The Codespace will automatically:
- Install all required development tools
- Set up a local Kubernetes cluster
- Configure necessary environment variables
- Install the Extralit packages in development mode

### 2. Deploying the Services

Once your Codespace is ready:

1. Open a terminal in the Codespace and deploy the services using Tilt:

   ```bash
   ENV=dev DOCKER_REPO=localhost:5005 tilt up
   ```

2. Monitor deployment in the Tilt UI at `http://localhost:10350`, which will be automatically forwarded

3. If you encounter PV (Persistent Volume) issues, deploy services incrementally:

   ```bash
   ENV=dev DOCKER_REPO=localhost:5005 tilt up elasticsearch
   ENV=dev DOCKER_REPO=localhost:5005 tilt up main-db
   ENV=dev DOCKER_REPO=localhost:5005 tilt up minio
   ENV=dev DOCKER_REPO=localhost:5005 tilt up weaviate
   ENV=dev DOCKER_REPO=localhost:5005 tilt up
   ```

### 3. Alternative: Start the Development Server Directly

If you prefer not to use Tilt, you can start the server directly:

```bash
# Check running containers
docker ps

# Start the development server
cd argilla-server
pdm run server-dev
```

### 4. Access the Web Interface

- Look for port 6900 in the "Ports" tab of your Codespace
- Click on the link to open the Extralit web interface
- Log in with the default credentials:
  - Username: `argilla`
  - Password: `1234`
  - API Key: `argilla.apikey`

### 5. Development Workflow

- **Backend Development**: Changes to `src/argilla_server/` or `src/extralit/` are automatically updated while Tilt is running
- **Frontend Development**: For frontend changes:
  ```bash
  cd argilla/argilla-frontend
  npm install
  npm run dev
  ```
## Option 2: Local Development Setup

### Prerequisites

- Python 3.9 or later
- Node.js 18 or later
- Docker and Docker Compose
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/extralit/extralit.git
cd extralit
```

### 2. Set Up Python Environment

We recommend using PDM for package management:

```bash
# Install PDM if not already installed
pip install pdm

# Install server dependencies
cd argilla-server
pdm install

# Install client dependencies
cd ../argilla
pdm install --dev
```

### 3. Build the Frontend

```bash
cd argilla-frontend
npm install
npm run build

# Copy built files to server static directory
cp -r dist ../argilla-server/src/argilla_server/static
```

### 4. Configure Environment Variables

Create a `.env.dev` file in the `argilla-server` directory with the following content:

```
ALEMBIC_CONFIG=src/argilla_server/alembic.ini
ARGILLA_AUTH_SECRET_KEY=8VO7na5N/jQx+yP/N+HlE8q51vPdrxqlh6OzoebIyko=
ARGILLA_DATABASE_URL=sqlite+aiosqlite:///${HOME}/.argilla/argilla-dev.db?check_same_thread=False
# Search engine configuration
ARGILLA_SEARCH_ENGINE=elasticsearch
ARGILLA_ELASTICSEARCH=http://localhost:9200
# Redis configuration
ARGILLA_REDIS_URL=redis://localhost:6379/0
```

### 5. Set Up the Databases

#### Vector database (Elasticsearch)

```sh
# Extralit supports ElasticSearch versions >=8.5
docker run -d --name elasticsearch-for-extralit -p 9200:9200 -p 9300:9300 -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" -e "discovery.type=single-node" -e "xpack.security.enabled=false" docker.elastic.co/elasticsearch/elasticsearch:8.5.3
```

#### Relational database (PostgreSQL)

```sh
docker run -d --name postgres-for-extralit -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres postgres:14
```

Alternatively, you can start all required services using Docker Compose:

```bash
# Start Elasticsearch and other services
docker-compose up -d elasticsearch redis
```

### 6. Run Database Migrations and Start the Server

```bash
cd argilla-server
pdm run migrate
pdm run cli database users create_default
pdm run server
```

### 7. Access the Web Interface

Open your browser and navigate to http://localhost:6900

## Option 3: Advanced Kubernetes Setup

For developers who want to work with Kubernetes locally:

### 1. Install Required Tools

- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Tilt](https://docs.tilt.dev/install.html)
- [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
- [ctlptl](https://github.com/tilt-dev/ctlptl/tree/main#how-do-i-install-it)

### 2. Create a Local Kubernetes Cluster

```bash
kind create cluster --name extralit-dev
```

### 3. Set Up Local Development with Image Registry

```bash
ctlptl create registry ctlptl-registry --port=5005
ctlptl create cluster extralit-dev --registry=ctlptl-registry
```

### 4. Apply Storage Configurations

```bash
ctlptl apply -f k8s/kind/kind-config.yaml
kubectl --context kind-kind taint node kind-control-plane node-role.kubernetes.io/control-plane:NoSchedule-
```

### 5. Create Namespace and Deploy Services

```bash
kubectl create ns extralit-dev
kubectl apply -f extralit-secrets.yaml -n extralit-dev
kubectl apply -f langfuse-secrets.yaml -n extralit-dev
kubectl apply -f weaviate-api-keys.yaml -n extralit-dev
```

### 6. Deploy with Tilt

```bash
ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace extralit-dev --context kind-extralit-dev
```

## Option 4: Docker Deployment

For a simpler setup using Docker without development capabilities:

### 1. Create a Project Directory

```bash
mkdir extralit && cd extralit
```

### 2. Download Docker Compose Configuration

```bash
wget -O docker-compose.yaml https://raw.githubusercontent.com/extralit/extralit/main/examples/deployments/docker/docker-compose.yaml
```

Or using curl:

```bash
curl https://raw.githubusercontent.com/extralit/extralit/main/examples/deployments/docker/docker-compose.yaml -o docker-compose.yaml
```

### 3. Start the Services

```bash
docker compose up -d
```

### 4. Access the Web Interface

Open your browser and navigate to http://localhost:6900

## Development Best Practices

### Linting and Formatting

To maintain a consistent code format, install the `pre-commit` hooks to run before each commit automatically.

```sh
pre-commit install
```

In addition, run the following scripts to check the code formatting and linting:

```sh
pdm run format
pdm run lint
```

??? tip "Running linting, formatting, and tests"
    You can run all the checks at once by using the following command:

    ```sh
    pdm run all
    ```

## Documentation Development

To contribute to the documentation and generate it locally:

```sh
mkdocs serve
```

This will start a local server with the documentation site.

## Troubleshooting

### Elasticsearch Issues

If you encounter issues with Elasticsearch:

```bash
# Check Elasticsearch logs
docker logs elasticsearch-for-extralit

# Ensure Elasticsearch is running
curl http://localhost:9200
```

### Database Migration Failures

If database migrations fail:

```bash
# Reset the database
rm -rf ~/.argilla/argilla-dev.db
pdm run migrate
```

### Frontend Build Issues

If you encounter issues with the frontend build:

```bash
# Clean and rebuild
cd argilla-frontend
rm -rf node_modules
npm install
npm run build
```

### Persistent Volume & Storage Class Issues

When using Kubernetes, persistent volume issues can occur:
- PVs might not be available when services are deployed, especially in `kind` clusters
- PVC might bind to incorrect PVs depending on creation order
- For persistent storage issues, check the `uncategorized` resource in Tilt
- Sometimes clearing `/tmp/kind-volumes/` and restarting the cluster is needed

### Deployment Issues

Common deployment problems:
- `elasticsearch`: Can fail on restart due to data-shard issues
- `main-db` Postgres: May fail to remount volumes after redeployment due to password changes

## Next Steps

After setting up your development environment:

1. Create a new project in the UI
2. Upload sample documents
3. Define extraction schemas
4. Run extractions
5. Review and annotate data

For more information on using Extralit, see the [Quickstart Guide](quickstart.md).

For support, join the [Extralit Slack channel](https://join.slack.com/t/extralit/shared_invite/zt-32blg3602-0m0XewPBXF7776BQ3m7ZlA).

