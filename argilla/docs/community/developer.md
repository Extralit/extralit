---
description: This is a step-by-step guide to help you contribute to the Extralit project as a developer. We are excited to have you on board! 🚀
hide:
 - footer
---

# Developer Guide

As an Extralit developer, you are already part of the community, and your contribution is valuable to our development. This guide will help you set up your development environment and start contributing.

!!! note "Extralit core components"

    - **Documentation**: Extralit's documentation serves as an invaluable resource, providing a comprehensive and in-depth guide for users seeking to explore, understand, and effectively harness the core components of the Extralit ecosystem.

    - **Python SDK**: A Python SDK installable with `pip install extralit` to interact with the Extralit Server and the Extralit UI. It provides an API to manage the data, configuration, and extraction workflows.

    - **FastAPI Server**: The core of Extralit is a Python `FastAPI server` that manages the data by pre-processing it and storing it in the vector database. Also, it stores application information in the relational database. It provides an REST API that interacts with the data from the Python SDK and the Extralit UI. It also provides a web interface to visualize the data.

    - **Relational Database**: A relational database to store the metadata of the records and the annotations. `PostgreSQL` is used as the primary database option and is deployed separately with the Extralit Server.

    - **Vector Database**: A vector database to store the records data and perform scalable vector similarity searches and basic document searches. We currently support `ElasticSearch` and `Weaviate`, which can be deployed as separate Docker images.

    - **Vue.js UI**: A web application to visualize, extract and validate your data, users, and teams. It is built with `Vue.js` and is directly deployed alongside the Extralit Server within our Extralit Docker image.

## Environment setup

Extralit offers a comprehensive guide for setting up your development environment. For detailed instructions, please refer to our [Development Environment Setup Guide](../getting_started/development_setup.md).

This guide covers everything you need to get started, including:

- Installing prerequisites
- Setting up Docker containers
- Configuring your development environment
- Running Extralit components locally

Once you have your environment set up, you can return to this guide to learn more about the specific components you want to contribute to.

## The Extralit repository

The Extralit repository has a monorepo structure, which means that all the components are located in the same repository: [`extralit/extralit`](https://github.com/extralit/extralit). This repo is divided into the following folders:

- [`extralit`](https://github.com/extralit/extralit/tree/develop/argilla/src/extralit): The FastAPI server project for extraction
- [`argilla/docs`](https://github.com/extralit/extralit/tree/develop/argilla/docs): The documentation project
- [`extralit`](https://github.com/extralit/extralit/tree/develop/argilla): The argilla SDK project
- [`argilla-server`](https://github.com/extralit/extralit/tree/develop/argilla-server): The FastAPI server project for annotation
- [`argilla-frontend`](https://github.com/extralit/extralit/tree/develop/argilla-frontend): The Vue.js UI project
- [`examples`](https://github.com/extralit/extralit/tree/develop/examples): Example resources for deployments, scripts and notebooks

!!! note "How to contribute?"
    Before starting to develop, we recommend reading our [contribution guide](contributor.md) to understand the contribution process and the guidelines to follow. Once you have [cloned the Extralit repository](contributor.md#fork-the-extralit-repository) and [checked out to the correct branch](contributor.md#create-a-new-branch), you can start setting up your development environment.

## Manual Setup: Alternative Development Options

If you prefer not to use Codespaces, you can set up your development environment manually using the following approaches.

### Set up the Python environment

To work on the Extralit Python SDK, you must install the Extralit package on your system.

!!! tip "Create a virtual environment"
    We recommend creating a dedicated virtual environment for SDK development to prevent conflicts. For this, you can use the manager of your choice, such as `venv`, `conda`, `pyenv`, or `uv`.

From the root of the cloned Extralit repository, you should move to the `extralit` folder in your terminal.

```sh
cd extralit
```

Next, activate your virtual environment and make the required installations:

```sh
# Install the `pdm` package manager
pip install pdm

# Install extralit in editable mode and the development dependencies
pdm install --dev
```

### Linting and formatting

To maintain a consistent code format, install the `pre-commit` hooks to run before each commit automatically.

```sh
pre-commit install
```

In addition, run the following scripts to check the code formatting and linting:

```sh
pdm run format
pdm run lint
```

### Running tests

Running tests at the end of every development cycle is indispensable to ensure no breaking changes.

```sh
# Run all tests
pdm run tests

# Run specific tests
pytest tests/integration
pytest tests/unit
```

??? tip "Running linting, formatting, and tests"
    You can run all the checks at once by using the following command:

    ```sh
        pdm run all
    ```

### Manual Kubernetes Setup

If you want to set up a local Kubernetes cluster manually:

1. Install required tools:
   - [kubectl](https://kubernetes.io/docs/tasks/tools/)
   - [Tilt](https://docs.tilt.dev/install.html)
   - [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
   - [ctlptl](https://github.com/tilt-dev/ctlptl/tree/main#how-do-i-install-it)

2. Create a local Kubernetes cluster:
   ```bash
   kind create cluster --name extralit-dev
   ```

3. For local development with image registry:
   ```bash
   ctlptl create registry ctlptl-registry --port=5005
   ctlptl create cluster extralit-dev --registry=ctlptl-registry
   ```

4. Apply storage configurations:
   ```bash
   ctlptl apply -f k8s/kind/kind-config.yaml
   kubectl --context kind-kind taint node kind-control-plane node-role.kubernetes.io/control-plane:NoSchedule-
   ```

5. Create namespace and deploy services:
   ```bash
   kubectl create ns extralit-dev
   kubectl apply -f extralit-secrets.yaml -n extralit-dev
   kubectl apply -f langfuse-secrets.yaml -n extralit-dev
   kubectl apply -f weaviate-api-keys.yaml -n extralit-dev
   ```

6. Deploy with Tilt:
   ```bash
   ENV=dev DOCKER_REPO=localhost:5005 tilt up --namespace extralit-dev --context kind-extralit-dev
   ```

### Set up the databases directly

If you prefer to run the databases directly without Kubernetes:

#### Vector database

```sh
# Extralit supports ElasticSearch versions >=8.5
docker run -d --name elasticsearch-for-extralit -p 9200:9200 -p 9300:9300 -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" -e "discovery.type=single-node" -e "xpack.security.enabled=false" docker.elastic.co/elasticsearch/elasticsearch:8.5.3
```

#### Relational database

```sh
docker run -d --name postgres-for-extralit -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=postgres postgres:14
```

## Set up the documentation

Documentation is essential to provide users with a comprehensive guide about Extralit.

!!! note "From `main` or `develop`?"
    If you are updating, improving, or fixing the current documentation without a code change, work on the `main` branch. For new features or bug fixes that require documentation, use the `develop` branch.

To contribute to the documentation and generate it locally, ensure you installed the development dependencies as shown in the ["Set up the Python environment"](#set-up-the-python-environment) section, and run the following command to create the development server with `mkdocs`:

```sh
mkdocs serve
```

### Documentation guidelines

As mentioned, we use [`mkdocs`](https://www.mkdocs.org/) to build the documentation. You can write the documentation in [`markdown`](https://www.markdownguide.org/getting-started/) format, and it will automatically be converted to HTML. In addition, you can include elements such as tables, tabs, images, and others, as shown in this [guide](https://squidfunk.github.io/mkdocs-material/reference/). We recommend following these guidelines:

- **Use clear and concise language**: Ensure the documentation is easy to understand for all users by using straightforward language and including meaningful examples. Images are not easy to maintain, so use them only when necessary and place them in the appropriate folder within the `docs/assets/images` directory.
- **Verify code snippets**: Double-check that all code snippets are correct and runnable.
- **Review spelling and grammar**: Check the spelling and grammar of the documentation.
- **Update the table of contents**: If you add a new page, include it in the relevant `index.md` or the `mkdocs.yml` file.

!!! note "Contribute with a tutorial"
    You can also contribute a tutorial (`.ipynb`) to the "Community" section. We recommend aligning the tutorial with the structure of the existing tutorials. For an example, check [this tutorial](../tutorials/getting_started.ipynb).

## Troubleshooting

### Persistent Volume & Storage Classes
When using Kubernetes, persistent volume issues can occur:
- PVs might not be available when services are deployed, especially in `kind` clusters
- PVC might bind to incorrect PVs depending on creation order
- For persistent storage issues, check the `uncategorized` resource in Tilt
- Sometimes clearing `/tmp/kind-volumes/` and restarting the cluster is needed

### Deployment Issues
Common deployment problems:
- `elasticsearch`: Can fail on restart due to data-shard issues
- `main-db` Postgres: May fail to remount volumes after redeployment due to password changes

For support, join the [Extralit Slack channel](https://join.slack.com/t/extralit/shared_invite/zt-32blg3602-0m0XewPBXF7776BQ3m7ZlA).

