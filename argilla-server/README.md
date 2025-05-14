<h1 align="center">
  <a href=""><img src="https://github.com/extralit/extralit/raw/develop/argilla/docs/assets/logo.svg" alt="Extralit" width="150"></a>
  <br>
  Extralit Server
  <br>
</h1>
<h3 align="center">Extract structured data from scientific literature with human validation</h2>

<p align="center">
<a href="https://pypi.org/project/extralit/">
<img alt="CI" src="https://img.shields.io/pypi/v/extralit.svg?style=flat-round&logo=pypi&logoColor=white">
</a>
<img alt="Codecov" src="https://codecov.io/gh/extralit/extralit/branch/main/graph/badge.svg"/>
<a href="https://pepy.tech/project/extralit">
<img alt="Downloads" src="https://static.pepy.tech/personalized-badge/extralit?period=month&units=international_system&left_color=grey&right_color=blue&left_text=pypi%20downloads/month">
</a>
</p>

<p align="center">
<a href="https://www.linkedin.com/company/extralit-ai">
<img src="https://img.shields.io/badge/linkedin-blue?logo=linkedin"/>
</a>
</p>

This repository contains developer information about the backend server components. For general usage, please refer to our [main repository](https://github.com/extralit/extralit) or our [documentation](https://docs.extralit.ai/latest/).

## Source Code Structure

The server components are split into two main services:

```
/extralit_server
  /api # Core extraction API endpoints
    /handlers # FastAPI request handlers 
    /schemas # Data models and validation
    /services # Business logic services
    /utils # Helper utilities
  /ml # Machine learning components
    /extractors # Document extraction models
    /ocr # OCR processing
    /pipeline # Extraction pipeline orchestration
  /storage # Data persistence layer
    /models # Database models
    /search # Search engine integration
    /vector # Vector store
```

```
/argilla_server 
  /api # Annotation UI API endpoints
    /handlers
    /schemas 
  /models # Database models
  /auth # Authentication
  /tasks # Background jobs
```

## Development Environment

The development environment uses Docker Compose to run all required services. Key commands:

```sh
# Start all services
docker-compose up -d

# Run server in dev mode
pdm run dev

# Run tests
pdm test

# Format and lint
pdm format
pdm lint

# Run all checks
pdm all
```

## Key Components

### FastAPI Servers

- **Extraction Server**: Handles document processing, extraction pipeline, and ML model serving
- **Annotation Server**: Manages UI, data validation workflow, and user collaboration

### Databases

- **PostgreSQL**: Main database for user data, annotations, and metadata
- **Elasticsearch**: Vector store for semantic search and document indexing
- **Weaviate**: Vector database for table and section embeddings

### Background Processing

Uses Celery for asynchronous tasks like:

- Document OCR and preprocessing
- ML model inference
- Batch extraction jobs
- Data export

## CLI Commands

Key management commands:

```sh
# Database management
python -m extralit_server db migrate
python -m extralit_server db create-user

# Start servers
python -m extralit_server start
python -m argilla_server start

# Run workers
python -m extralit_server worker
```

See full CLI documentation in our [developer docs](https://docs.extralit.ai/latest/developer).

## Contributing

Check our [contribution guide](https://docs.extralit.ai/latest/community/contributor) and join our [Slack community](https://join.slack.com/t/extralit/shared_invite/zt-2kt8t12r7-uFj0bZ5SPAOhRFkxP7ZQaQ).

## Roadmap

See our [development roadmap](https://github.com/orgs/extralit/projects/2/views/1) and share your ideas!
