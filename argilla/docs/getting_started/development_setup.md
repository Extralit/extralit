---
description: Comprehensive setup instructions for Extralit development
---

# Development Setup

This guide provides detailed instructions for setting up the Extralit development environment using different approaches, from beginner-friendly options to advanced configurations.

## Option 1: GitHub Codespaces (Recommended for Beginners)

GitHub Codespaces provides a fully configured cloud development environment with all necessary tools pre-installed, making it the easiest way to get started.

The Codespaces will automatically:
- Install all required development tools
- Set up a local Kubernetes cluster
- Configure necessary environment variables
- Install the Extralit packages in development mode

### 1. Setting Up a Codespace

=== "New Contributors (Fork)"
    This approach is recommended for contributors who don't have direct write access to the main repository:

    1. Fork the [Extralit repository](https://github.com/extralit/extralit) to your GitHub account
    2. Navigate to your forked repository
    3. Click the "Code" button
    4. Select the "Codespaces" tab
    5. Click on the kabob menu to select "New with options..." to launch a new development environment

=== "Existing Contributors"
    This approach is for maintainers and contributors with direct push access to the main Extralit repository:

    1. Use this direct link to create a Codespace with the preferred configuration:
       [Create Extralit Codespace](https://github.com/codespaces/new?skip_quickstart=true&machine=standardLinux32gb&repo=708248756&ref=develop&devcontainer_path=.devcontainer%2Fdevcontainer.json)
    2. Select your preferred machine type (recommended: 4-core, 16GB RAM)
    3. Click "Create codespace"

### 2. Selecting a Development Environment

Extralit offers three different development environments through devcontainers, each optimized for different purposes:

=== "Tilt on K8s (Recommended)"
    This environment provides full-stack development with Kubernetes and live-reloading capabilities:
    
    ```bash
    # Initialize the Kubernetes cluster and deploy all services
    tilt up
    ```

    Then, simply monitor the deployment in the Tilt UI. The URL will be available in the "Ports" tab, usually http://localhost:10350, or another URL in your VSCode Ports tab.
    
    **Advanced Configuration:** You can customize your deployment by setting environment variables:
    
    ```bash
    # Use external database instead of deploying PostgreSQL
    export ARGILLA_DATABASE_URL="postgresql://user:password@external-host:5432/dbname"
    
    # Use external S3-compatible storage instead of deploying MinIO
    export S3_ENDPOINT="https://your-s3-endpoint"
    export S3_ACCESS_KEY="your-access-key"
    export S3_SECRET_KEY="your-secret-key"
    
    # Use external OpenAI API key
    export OPENAI_API_KEY="your-openai-api-key"
    
    # Use external Weaviate instance
    export WCS_HTTP_URL="https://your-weaviate-instance"
    export WCS_GRPC_URL="grpc://your-weaviate-instance:50051"
    export WCS_API_KEY="your-weaviate-api-key"
    
    # Start Tilt with custom configuration
    tilt up
    ```


=== "Docker Compose"
    This environment uses Docker Compose for a simpler, leaner setup without Kubernetes:
    
    ```bash
    # Start all required services using Docker Compose (if not already started automatically in the devcontainer)
    cd .devcontainer/docker-compose
    docker-compose up -d
    
    # Install server dependencies
    cd argilla-server
    pdm install
    
    # Start the server in development mode
    pdm run server-dev
    ```

=== "UI/UX Design Only"
    This lightweight environment is focused solely on frontend development for UI changes only. It will connect directly to a public demo HF Spaces server instance and automatically load the live-reloading frontend as you make changes.
    
    If 
    ```bash
    # Navigate to the frontend directory
    cd argilla-frontend
    
    # Install dependencies
    npm install
    
    # Start the development server with mock API
    API_BASE_URL=https://extralit-public-demo.hf.space/ npm run dev
    ```
    
### 3. Development workflow*

    - **Backend Development**: Changes to `argilla_server/src/argilla_server/` or `argilla/src/{argilla,extralit}/` are automatically updated if Tilt is running
    - **Python SDK packages**
      ```bash
      cd argilla
      pdm install
      ```
    - **Frontend Development**: For frontend live-reloading:
      ```bash
      cd argilla/argilla-frontend
      npm install
      npm run dev
      ```



### 4. Access the Web Interface

- Look for port 6900 in the "Ports" tab of your Codespace
- Click on the link to open the Extralit web interface
- Log in with the default credentials:
  - Username: `argilla`
  - Password: `1234`
  - API Key: `argilla.apikey`




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

