
<h1 align="center">
  <a href=""><img src="https://github.com/extralit/extralit/blob/develop/argilla/docs/assets/logo.png" alt="Extralit" width="500"></a>
</h1>

<h2 align="center">Open-source feedback layer for LLM-assisted data extractions</h2>

<h3>
<p align="center">
<a href="#">📄 Documentation</a> | </span>
<a href="#-quickstart">🚀 Quickstart</a> <span> | </span>
<a href="#-project-architecture">🛠️ Architecture</a> <span> | </span>
</p>
</h3>

## What is Extralit?

<img src="docs/_source/_static/images/main/data-extraction-pipeline.jpg" alt="pipeline">

Extralit is a UI interface and platform for LLM-based document data extraction that integrates human and model feedback loops for continuous LLM refinement and data extraction oversight.

With a Python SDK and adaptable UI, you can create human and model-in-the-loop workflows for:

- Schema-driven extraction: Ensures high specificity, contextual relevance, and automated validation of the extracted data.
- Advanced PDF preprocessing: AI optical character recoginition (OCR) algorithms to detect and correct table structures within documents.
- User-friendly interface: Facilitates easy verification and correction of extracted data.
- Data flywheel: Continuous data collection of table extractions and LLM outputs to monitor performance and build datasets.


## Getting started

### Installation
Install the client package

```bash
pip install extralit
```
After installing this client package, you can manage your extraction workspace through the CLI.

```base
extralit login --api-url http://<path_to_the_webserver>
# You will be prompted an API key to login to your account, which can be obtained from User Settings in the web interface
```

## 🛠️ Project Architecture

Argilla is built on 5 core components:

- **Python SDK**: A Python SDK which is installable with `pip install extralit`. To interact with the Argilla Server and the Argilla UI. It provides an API to manage the data, configuration and annotation workflows.
- **FastAPI Server**: The core of Argilla is a *Python FastAPI* server that manages the data, by pre-processing it and storing it in the vector database. Also, it stores application information in the relational database. It provides a REST API to interact with the data from the Python SDK and the Argilla UI. It also provides a web interface to visualize the data.
- **Relational Database**: A relational database to store the metadata of the records and the annotations. *SQLite* is used as the default built-in option and is deployed separately with the Argilla Server but a separate *PostgreSQL* can be used too.
- **Vector Database**: A vector database to store the records data and perform scalable vector similarity searches and basic document searches. We currently support *ElasticSearch* and *AWS OpenSearch* and they can be deployed as separate Docker images.
- **Vue.js UI**: A web application to visualize and annotate your data, users and teams. It is built with *Vue.js* and is directly deployed alongside the Argilla Server within our Argilla Docker image.

## Repo Activity

![Alt](https://repobeats.axiom.co/api/embed/503055f15ba7ac2f51d697153f7c146ae81c6c04.svg "Repobeats analytics image")

