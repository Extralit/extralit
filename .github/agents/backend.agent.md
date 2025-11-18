---
name: Python Backend and SDK Developer
description:
---

# Extralit Repo Overview

Extralit (https://github.com/Extralit/extralit) is a multi-component system for scientific literature data extraction with human-in-the-loop workflows:

- **extralit-server/**: FastAPI backend server with PostgreSQL database, handles users, datasets, records, and API interactions
- **extralit-frontend/**: Vue.js/Nuxt.js web UI for data visualization, annotation, and team collaboration
- **extralit/**: Python SDK client library for programmatic interaction with the server
- **Vector Database**: External Elasticsearch/OpenSearch for scalable vector similarity searches

## Development Commands

### Server (extralit-server/)
```bash
cd extralit-server/
pdm run server-dev       # Start server with db migration init + auto-reload
pdm run server           # Start server only
pdm run worker           # Start background worker only
pdm run migrate          # Run database migrations
pdm run test             # Run tests
```


### Client SDK (extralit/)
```bash
cd extralit/
pdm run test             # Run tests
pdm run lint             # Run ruff linting
```

## Key Development Notes

### Backend Structure
- FastAPI with SQLAlchemy ORM and Alembic migrations
- Background job processing with Redis Queue (rq)
- OAuth2 authentication with JWT tokens
- Webhook system for external integrations
- Document processing with OCR capabilities

### Database Management
- Alembic handles all database schema changes
- Use `pdm run revision` to create new migrations after model changes
- Always run `pdm run migrate` before starting development

### Testing
- Backend: pytest with async support, factory-boy for fixtures
- Frontend: Jest for unit tests, Playwright for e2e
- Python packages require Python 3.9+ (extralit) or 3.10+ (extralit-server)
- Node.js 18+ required for frontend

### Container Environment
- Docker Compose setup available for full stack development
- Services: Elasticsearch, Redis, MinIO for file storage
- See `.github/workflows/copilot-setup-steps.yml` for complete environment setup

### Linting Configuration
- Python: Ruff with shared configuration across packages
- Pre-commit hooks for code formatting and linting

# `extralit-server/` Backend Architecture Overview

Extralit-server is the FastAPI backend component of the Extralit ecosystem for scientific literature data extraction with human-in-the-loop workflows. This server handles:

- **User Management**: Authentication, authorization, workspaces, and role-based access
- **Dataset Management**: Scientific literature datasets with metadata, fields, and questions
- **Record Processing**: Document records with responses, suggestions, and annotations
- **Background Jobs**: Asynchronous document processing, OCR, and ML inference via Redis Queue (rq)
- **Vector Search**: Integration with Elasticsearch/OpenSearch for semantic similarity searches
- **Webhook System**: Event notifications and external integrations
- **File Storage**: Document management with MinIO S3-compatible storage

## Development Commands

```bash
# Core development workflow
pdm run server-dev        # Start server with auto-reload + worker + migrations
pdm run server           # Start server only (production mode)
pdm run worker           # Start background worker only
pdm run migrate          # Run database migrations
pdm run revision         # Create new Alembic migration after model changes

# Testing and quality
pdm run test             # Run pytest test suite
pdm run test-cov         # Run tests with coverage report
pdm run lint             # Run ruff linting (required before commits)

# Database management
pdm run cli database migrate                    # Run migrations
pdm run cli database users create_default      # Create default admin user
pdm run cli database users create              # Interactive user creation
pdm run cli database revisions                 # Generate migration files

# Background job management
pdm run cli worker       # Start RQ worker for background jobs

# Search engine management
pdm run cli search_engine reindex             # Reindex all datasets in search engine
```

## Key Architecture Patterns

### FastAPI Application Structure
- **Main App**: `src/extralit_server/_app.py` - Application factory with middleware, CORS, and lifespan management
- **API Routes**: `src/extralit_server/api/routes.py` - Centralized router configuration for v1 API
- **Route Handlers**: `src/extralit_server/api/handlers/v1/` - Request handlers organized by domain
- **Schemas**: `src/extralit_server/api/schemas/v1/` - Pydantic request/response models
- **Policies**: `src/extralit_server/api/policies/v1/` - Authorization and access control logic

### Database Layer (SQLAlchemy + Alembic)
- **Models**: `src/extralit_server/models/database.py` - Core domain models (User, Workspace, Dataset, Record, etc.)
- **Base Model**: `src/extralit_server/models/base.py` - Abstract base with common CRUD operations
- **Migrations**: `src/extralit_server/alembic/versions/` - Database schema evolution
- **Connection**: `src/extralit_server/database.py` - Async database session management

### Background Job Processing (RQ)
- **Queue Setup**: `src/extralit_server/jobs/queues.py` - Redis connection and queue configuration
- **Job Modules**: `src/extralit_server/jobs/` - Background tasks for documents, imports, OCR, webhooks
- **Worker**: Started via `pdm run worker` for processing async tasks

### Search Engine Integration
- **Abstraction**: `src/extralit_server/search_engine/base.py` - Common interface for search engines
- **Implementations**:
  - `src/extralit_server/search_engine/elasticsearch.py`
  - `src/extralit_server/search_engine/opensearch.py`
- **Configuration**: Set via `EXTRALIT_SEARCH_ENGINE` environment variable

### Context Layer (Business Logic)
- **Contexts**: `src/extralit_server/contexts/` - Domain-specific business logic separate from API handlers
- **Examples**: `accounts.py`, `datasets.py`, `records.py`, `imports.py`
- **Pattern**: Contexts handle complex operations, validation, and cross-domain logic

### Authentication & Security
- **OAuth2**: `src/extralit_server/security/authentication/oauth2/` - OAuth2 provider integrations
- **JWT**: `src/extralit_server/security/authentication/jwt.py` - Token-based authentication
- **API Keys**: `src/extralit_server/security/authentication/db/api_key_backend.py` - Alternative auth method

## Environment Configuration

Key environment variables (prefixed with `EXTRALIT_`):
```bash
EXTRALIT_DATABASE_URL=sqlite+aiosqlite:///extralit.db    # Database connection
EXTRALIT_REDIS_URL=redis://localhost:6379/0             # Redis for background jobs
EXTRALIT_ELASTICSEARCH=http://localhost:9200            # Search engine endpoint
EXTRALIT_SEARCH_ENGINE=elasticsearch                    # elasticsearch|opensearch
EXTRALIT_S3_ENDPOINT=http://localhost:9000              # MinIO/S3 storage
EXTRALIT_CORS_ORIGINS=["*"]                             # CORS configuration
```

## Testing Strategy

- **Unit Tests**: `tests/unit/` - Component-level testing with mocking
- **Integration Tests**: Database and external service integration testing
- **Factories**: `tests/factories.py` - Test data generation with factory-boy
- **Async Testing**: pytest-asyncio for async database and API operations
- **Test Database**: Isolated test database created per test session

## Important Development Notes

### Database Migrations
- Always run `pdm run revision` after model changes to generate migrations
- Review generated migrations before applying with `pdm run migrate`
- Never edit existing migration files; create new ones for changes

### Background Job Development
- Jobs defined in `src/extralit_server/jobs/` are executed by separate worker processes
- Use `HIGH_QUEUE` for time-sensitive jobs, `DEFAULT_QUEUE` for regular processing
- Jobs should be idempotent and handle failures gracefully

### Search Engine Operations
- Dataset records are automatically indexed/updated in the search engine
- Use `pdm run cli search_engine reindex` after significant data changes
- Search operations are asynchronous and may have eventual consistency

### Security Considerations
- All API endpoints require authentication (JWT tokens or API keys)
- Workspace-based authorization controls data access
- Sensitive operations require specific user roles (admin, owner)
- Environment variables should never contain secrets in production

### File Processing
- Document uploads trigger background OCR and preprocessing jobs
- Large files are processed asynchronously to avoid blocking API requests
- File storage integrates with MinIO for scalable object storage

# `extralit/` Python Client SDK Architecture Overview

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
- **Black Formatting**: Line length 120
- **pytest**: Async support, custom fixtures, environment variable handling

### Testing Structure
- **Unit Tests**: `tests/unit/` - Component-level testing with mocks
- **Integration Tests**: `tests/integration/` - Full API interaction testing
- **Test Organization**: Mirrors source structure with dedicated API, CLI, and model tests

### Entry Points
- Package exposes `extralit` console script pointing to `extralit.cli.app:app`
- Main client class accessible via `from extralit import Extralit`
- Modular imports for specific components (datasets, records, workspaces, etc.)

# Data Aggregation and Normalization Architecture

Extralit uses a normalized database approach for storing and presenting extracted data. Each document's extractions are split into separate records (like database tables) with reference keys connecting them, similar to a relational database schema.

## Document Data Extraction Flow

1. **PaperExtraction Model** (`extralit/src/extralit/extraction/models/paper.py`)
   - Central container for a document's extraction data
   - Contains multiple pandas DataFrames organized by schema name
   - Holds SchemaStructure defining data organization across schemas

2. **Data Normalization Process** (`extralit/src/extralit/pipeline/export/record.py`)
   - **Document-Level Record**: Creates a single "publication" record for document metadata
     - Based on singleton schema in SchemaStructure
     - Created by `create_publication_records()` function
   - **Schema-Level Records**: Creates separate "extraction" records for each schema
     - Each record contains one DataFrame of extracted data as serialized JSON
     - Created by `create_extraction_records()` function
     - References connect to the publication record and other extraction records

3. **Dataset Configuration** (`extralit/src/extralit/pipeline/export/dataset.py`)
   - Defines structure of Extralit datasets to store normalized records
   - `create_papers_dataset()` configures datasets for document-level records
   - `create_extraction_dataset()` configures datasets for schema-level records


## Data Aggregation and Annotation Workflow

This section describes how extracted data from documents is structured, stored, and presented to the user for annotation. Extralit uses a relational database approach where data is split into different tables and linked through reference keys.

### 1. The `PaperExtraction` Model

- Core container for document extractions (`extralit/src/extralit/extraction/models/paper.py`)
- Holds multiple pandas DataFrames keyed by schema name
- Contains `SchemaStructure` (`extralit/src/extralit/extraction/models/schema.py`) that defines organization of schemas

### 2. Data Normalization into Extralit Records

Data from `PaperExtraction` is normalized into multiple `ex.Record` objects in Extralit datasets, separating document metadata from specific extractions:

- **Document-Level Record**: (`extralit/src/extralit/pipeline/export/record.py:create_publication_records()`)
  - Single "publication" record per document
  - Contains document metadata defined by "singleton" schema
  - Serves as the primary reference point for all extraction records

- **Schema-Level Records**: (`extralit/src/extralit/pipeline/export/record.py:create_extraction_records()`)
  - Separate record for each schema (authors, methods, results, etc.)
  - Each contains one DataFrame as serialized JSON
  - Contains reference columns connecting to the publication record

### 3. Frontend Annotation and Data Joining

The frontend presents normalized data as a unified view for annotation:

- **Table Display**: (`extralit-frontend/components/base/base-render-table/useSchemaTableViewModel.ts`)
  - Manages display and validation of individual tables
  - Identifies primary keys and reference columns
  - Configures table grouping based on references

- **Reference Resolution**: (`extralit-frontend/components/base/base-render-table/useReferenceTablesViewModel.ts`)
  - Identifies reference columns (`_ref` or `_ID` suffix)
  - Dynamically fetches related records from other tables
  - Joins data to create a unified table view for the annotator
  - Manages reference values and combinations for relationships

### 4. Dataset Configuration

- Dataset structure defined in `extralit/src/extralit/pipeline/export/dataset.py`
- `create_papers_dataset()` configures document-level metadata datasets
- `create_extraction_dataset()` configures schema-specific extraction datasets
- Each dataset includes proper field definitions, questions, and metadata properties


