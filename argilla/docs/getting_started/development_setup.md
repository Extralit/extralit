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

