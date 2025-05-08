
<h1 align="center">
  <a href=""><img src="https://github.com/extralit/extralit/blob/develop/argilla/docs/assets/logo.png" alt="Extralit" width="500"></a>
</h1>

<h3>
<p align="center">
<a href="https://docs.extralit.ai/latest/" target="_blank">📄 Documentation</a> | </span>
<a href="https://docs.extralit.ai/latest/getting_started/quickstart/" target="_blank">🚀 Quickstart</a> <span> | </span>
<a href="https://docs.extralit.ai/latest/community/developer/" target="_blank">🛠️ Architecture</a> <span>
</p>
</h3>

## What is Extralit?

Extralit (EXTRAct LITerature) is a data extraction workflow with user-friendly UI, designed for **LLM-assisted scientific data extraction** and other **unstructured document intelligence** tasks. It focuses on data accuracy above all else, and further integrates human feedback loops for continuous LLM refinement and collaborative data extraction.

- 🔹 Precision First – Built for high data accuracy, ensuring reliable results.
- 🔹 Human-in-the-Loop – Seamlessly integrate human annotations to refine LLM outputs and collaborate on data validation.
- 🔹 Flexible & Scalable – Available as a Python SDK, CLI, and Web UI with multiple deployment options to fit your workflow.

🌟 Key Features

- ✅ Schema-Driven Extraction – Define structured schemas for context-aware, high-accuracy data extraction across scientific domains.
- ✅ Advanced PDF Processing – AI-powered OCR detects complex table structures in both digital and scanned PDFs.
- ✅ Built-in Validation – Automatically verify extracted data for accuracy in both the annotation UI and the data pipeline outputs.
- ✅ User-Friendly Interface – Easily review, edit, and validate data with team-based consensus workflows.
- ✅ Data Flywheel – Collect human annotations to monitor performance and build fine-tuning datasets for continuous improvement.

Start extracting smarter with Extralit! 🚀

## Getting started

### Installation
Install the client package

```bash
pip install extralit
```

If you already have a server deployed and login credentials, obtain your API key in the User Settings. You can manage your extraction workspace through the CLI with:

```base
extralit login --api-url http://<extralit_server_instance>
# You will be prompted an API key to login to your account
```

### Server setup

See [https://docs.extralit.ai/latest/getting_started/quickstart/](https://docs.extralit.ai/latest/getting_started/quickstart/)

## 🛠️ Project Architecture

Extralit is built on top of Argilla, extending its capabilities with enhanced data extraction, validation, and human-in-the-loop workflows, with these 5 core components:

- **Python SDK**: A Python SDK which is installable with `pip install extralit` to interact with the web server and provides an API to manage the data extraction workflows.
- **FastAPI Server**: The backbone of Argilla, handling users, storage, and API interactions. It manages application data using a relational database (PostgreSQL by default).
- **Web UI**: A web application to visualize and annotate your data, users and teams. It is built with *Vue.js* and *Nuxt.js* and is directly deployed alongside the FastAPI Server within our Docker image.
- **Vector Database**: A vector database to store the records data and perform scalable vector similarity searches and basic document searches. We currently support *ElasticSearch* and *AWS OpenSearch* and they can be deployed as separate Docker images.

## Repo Activity

![Alt](https://repobeats.axiom.co/api/embed/503055f15ba7ac2f51d697153f7c146ae81c6c04.svg "Repobeats analytics image")

