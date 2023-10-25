
<h1 align="center">
  <a href=""><img src="https://github.com/dvsrepo/imgs/raw/main/rg.svg" alt="Argilla" width="150"></a>
  <br>
  ✨ Argilla ✨
  <br>
</h1>


<h2 align="center">Open-source feedback layer for LLMs</h2>
<br>


<br>

<h3>
<p align="center">
<a href="https://docs.argilla.io">📄 Documentation</a> | </span>
<a href="#-quickstart">🚀 Quickstart</a> <span> | </span>
<a href="#-project-architecture">🛠️ Architecture</a> <span> | </span>
</p>
</h3>

## What is Argilla?

Argilla is an open-source platform for data-centric LLM development. Integrates human and model feedback loops for continuous LLM refinement and oversight.

With Argilla's Python SDK and adaptable UI, you can create human and model-in-the-loop workflows for:

* Supervised fine-tuning
* Preference tuning (RLHF, DPO, RLAIF, and more)
* Small, specialized NLP models
* Scalable evaluation.

## 🚀 Development Quickstart

### Install the Pre-requisites
These development tools

1. Install [Docker Desktop](https://docs.docker.com/get-docker/)
2. Install [kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)
2. Install [ctlptl](https://github.com/tilt-dev/ctlptl/tree/main#how-do-i-install-it)
3. Install [Tilt](https://docs.tilt.dev/)

### Set up local infrastructure

1. Create a `kind` cluster
```bash
ctlptl create registry ctlptl-registry --port=5005
ctlptl create cluster kind --registry=ctlptl-registry
```


2. Apply config to mount local directory
> ctlptl apply -f k8s/kind/kind-config.yaml


### Start local development

1. Check

## 🛠️ Project Architecture

Argilla is built on 5 core components:

- **Python SDK**: A Python SDK which is installable with `pip install argilla`. To interact with the Argilla Server and the Argilla UI. It provides an API to manage the data, configuration and annotation workflows.
- **FastAPI Server**: The core of Argilla is a *Python FastAPI* server that manages the data, by pre-processing it and storing it in the vector database. Also, it stores application information in the relational database. It provides a REST API to interact with the data from the Python SDK and the Argilla UI. It also provides a web interface to visualize the data.
- **Relational Database**: A relational database to store the metadata of the records and the annotations. *SQLite* is used as the default built-in option and is deployed separately with the Argilla Server but a separate *PostgreSQL* can be used too.
- **Vector Database**: A vector database to store the records data and perform scalable vector similarity searches and basic document searches. We currently support *ElasticSearch* and *AWS OpenSearch* and they can be deployed as separate Docker images.
- **Vue.js UI**: A web application to visualize and annotate your data, users and teams. It is built with *Vue.js* and is directly deployed alongside the Argilla Server within our Argilla Docker image.

