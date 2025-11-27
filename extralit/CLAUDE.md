# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is the **extralit/** Python SDK client library - part of the larger Extralit multi-component system for scientific literature data extraction. The full system includes:

- **extralit-server/**: FastAPI backend server with PostgreSQL database, handles users, datasets, records, and API interactions
- **extralit-frontend/**: Vue.js/Nuxt.js web UI for data visualization, annotation, and team collaboration
- **extralit/**: This Python SDK client library for programmatic interaction with the server
- **Vector Database**: External Elasticsearch/OpenSearch for scalable vector similarity searches

This SDK package allows researchers to:
- Connect to Extralit servers via API
- Define custom extraction schemas and datasets
- Upload and manage scientific documents
- Extract structured data with AI assistance
- Export results for analysis

### Core Components

- **Client API** (`src/extralit/client/`): Main `Extralit` client class for server connections
- **CLI Interface** (`src/extralit/cli/`): Command-line tools for all operations (datasets, documents, extraction, etc.)
- **Data Models** (`src/extralit/_models/`): Pydantic models for records, settings, schemas, workspaces, and users
- **API Layer** (`src/extralit/_api/`): HTTP client and API endpoints for server communication
- **I/O Operations** (`src/extralit/datasets/_io/`): Dataset import/export with HuggingFace Hub integration

## Development Commands

### Testing and Quality
```bash
pdm run test             # Run pytest with warnings disabled
pdm run test-cov         # Run tests with coverage reporting
pdm run lint             # Run ruff linting
pdm run all              # Format, lint, and test in sequence
```

### Package Management
```bash
pdm install             # Install dependencies and development packages
pdm install --prod       # Install production dependencies only
```

### CLI Development
The package provides an `extralit` CLI command that registers multiple subcommands:
- `extralit datasets` - Dataset management
- `extralit documents` - Document upload and processing
- `extralit extraction` - Data extraction workflows
- `extralit schemas` - Schema definition and management
- `extralit workspaces` - Workspace operations
- `extralit users` - User management

## Key Development Notes

### Dependencies
- **Python Requirements**: 3.9.2+ (supports up to 3.13)
- **Core Dependencies**: httpx, pydantic, typer, rich, huggingface_hub
- **AI/ML Stack**: llama-index, weaviate-client, spacy, transformers
- **Optional Features**: OCR (`nougat-ocr`), PDF processing (`unstructured`), NLP (`textdescriptives`)

### Code Structure
- **Async/Sync API**: Uses httpx for async HTTP operations with sync wrappers
- **CLI Framework**: Built on Typer with custom `ExtralitTyper` extension
- **Model Architecture**: Pydantic v2 models with resource-based inheritance
- **Error Handling**: Custom exception hierarchy in `_exceptions/`

### Configuration
- **Ruff Linting**: Line length 120, comprehensive rule set including FastAPI-specific rules
- **pytest**: Async support, custom fixtures, environment variable handling

### Testing Structure
- **Unit Tests**: `tests/unit/` - Component-level testing with mocks
- **Integration Tests**: `tests/integration/` - Full API interaction testing
- **Test Organization**: Mirrors source structure with dedicated API, CLI, and model tests

### Entry Points
- Package exposes `extralit` console script pointing to `extralit.cli.app:app`
- Main client class accessible via `from extralit import Extralit`
- Modular imports for specific components (datasets, records, workspaces, etc.)