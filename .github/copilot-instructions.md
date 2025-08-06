# Extralit Codebase Organization Guide

This guide provides an overview of the Extralit codebase (https://github.com/Extralit/extralit) architecture to help new contributors understand how the project is organized. Extralit is a monorepo containing multiple interconnected components that work together to provide document extraction, processing, and annotation capabilities.

## Development Workflow
When contributing to Extralit, consider these guidelines:

1. **Understand the context**: Identify which domain context your change belongs to
2. **Follow existing patterns**: Look at similar implementations for guidance
3. **Maintain separation of concerns**:
   - Keep API handlers thin, delegating to contexts for business logic
   - Keep database models focused on structure, not behavior
   - Use validators for input validation
4. **Write tests**: Add tests for new functionality in the appropriate test directories
   - **Avoid running full test suite** - Only run specific test files: `pdm run test tests/unit/services/test_schemas.py -v`
   - **Most tests are better running in GH Actions** - focus on targeted testing during development
5. **Update docs**: Reflect the new changes made to the data architecture or refactored modules to `.github/copilot-instructions.md`.


## Repository Structure

Extralit is organized as a monorepo with several main components:

- **extralit/**: Python SDK and core extraction functionality
- **extralit-server/** (formerly extralit-server): Backend server implementation
- **argilla-frontend/**: Frontend web application (will be renamed to extralit-frontend in future)
- **examples/**: Sample implementations and deployment configurations

## Core Components

### Frontend (`argilla-frontend`)

The frontend is built with Vue.js and Nuxt.js, providing a modern web interface for document management, extraction, and annotation.

Key directories:
- `components/`: UI components organized by functionality
  - `base/`: Reusable UI components (buttons, inputs, modals, etc.)
  - `features/`: Feature-specific components (annotation, dataset creation, etc.)
- `pages/`: Application routes and page components
- `v1/`: Version 1 application logic
  - `v1/domain/`: Core domain entities and business logic, organized into
    - `entities/`: Domain entities
    - `events/`: Domain events (Event suffix)
    - `services/`: Domain service interfaces (I prefix)
    - `usecases/`: Use case implementations (kebab-case, use-case suffix)
  - `v1/infrastructure/`: Infrastructure implementations
    - `events/`: Event handlers (EventHandler suffix)
    - `repositories/`: API repository implementations (Repository suffix)
    - `services/`: UI hooks and utilities (use* pattern)
    - `storage/`: Storage clients (Storage suffix)
    - `types/`: Infrastructure types and API models
- `plugins/`: Vue.js plugins and extensions
- `assets/`: Static assets like styles, fonts, and images

### Key Frontend Patterns
- **Components**: Base components in `components/base/`, feature components in `components/features/`
- **Pages**: Nuxt.js file-based routing in `pages/`
- **Stores**: Pinia stores in `v1/store/`
- **Domain Logic**: Dependency injection in `v1/di/`
- **Axios**: @nuxt/axios with `{proxy: true, browserBaseURL: "api"}`
- **Styling**: SCSS in `assets/scss/`, component-scoped
- **View Models**: `setup(props) { return useViewModelName(props); }` pattern
- **BaseSimpleTable**: Use existing `BaseSimpleTable.vue` for tabular display

### Backend Server (`extralit-server/src/extralit_server`)

The backend is a FastAPI application that handles API requests, database operations, and search functionality.

Key modules:
- `api/`: API routes, handlers, and schemas
  - `handlers/`: Request handlers for different API endpoints
  - `schemas/`: Pydantic models for request/response validation
  - `policies/`: Access control policies
- `contexts/`: Core business logic organized by domain context
  - `datasets.py`: Dataset management operations
  - `files.py`: File handling operations
  - `accounts.py`: User account management
  - `search.py`: Search functionality
  - `webhooks.py`: Webhook event handling
- `models/`: Database models and ORM definitions
  - `database.py`: SQLAlchemy models for database entities
  - `mixins.py`: Shared model behaviors
- `search_engine/`: Search functionality implementation
  - `elasticsearch.py`: Elasticsearch integration
  - `opensearch.py`: OpenSearch integration
- `security/`: Authentication and authorization
  - `authentication/`: Authentication mechanisms
- `cli/`: Command-line interface tools
- `jobs/`: Background job processing
- `webhooks/`: Webhook processing and event handling
- `validators/`: Data validation logic

### SDK and Core Extraction (`extralit/src/extralit`)

The core extraction functionality and Python SDK for interacting with the Extralit system.

Key modules:
- `extraction/`: Document extraction capabilities
  - `chunking.py`: Text chunking algorithms
  - `extraction.py`: Core extraction logic
  - `vector_store.py`: Vector storage for semantic search
  - `vector_index.py`: Vector indexing functionality
  - `prompts.py`: LLM prompt templates
  - `models/`: ML models for extraction
- `schema/`: Schema definitions and validation
  - `dtypes/`: Data type definitions
  - `checks/`: Schema validation rules
  - `references/`: Reference management
- `preprocessing/`: Document preprocessing
  - `document.py`: Document processing logic
  - `segment.py`: Document segmentation
  - `tables.py`: Table extraction and processing
  - `text.py`: Text processing utilities
- `convert/`: Format conversion utilities
  - `pdf.py`: PDF processing
  - `html_table.py`: HTML table conversion
  - `json_table.py`: JSON table conversion
- `metrics/`: Evaluation metrics
- `server/`: Embedded server implementation
- `storage/`: Storage abstractions

## Architecture Concepts

### Context-Based Architecture

The backend follows a context-based architecture where business logic is organized by domain contexts. Each context (`datasets`, `files`, `accounts`, etc.) encapsulates related functionality and provides a clean API for the rest of the application.

For example, the `datasets.py` context handles all operations related to dataset management:
- Creating and updating datasets
- Adding and removing records
- Managing dataset settings
- Handling dataset permissions

This approach keeps related functionality together and makes the codebase more maintainable.

### Models and Database

The system uses SQLAlchemy for database operations with models defined in `extralit-server/src/extralit_server/models/database.py`. These models represent the core entities in the system:
- Users and workspaces
- Datasets and records
- Questions and responses
- Vectors and metadata

The models use mixins (defined in `mixins.py`) to share common functionality like timestamps, UUIDs, and soft deletion.

### API Structure

The API follows a RESTful design with endpoints organized by resource type. The implementation uses FastAPI's dependency injection for:
- Request validation
- Authentication and authorization
- Database session management
- Error handling

API handlers in `api/handlers/` implement the actual request processing logic, while schemas in `api/schemas/` define the request and response data structures.

### Authorization Patterns

Available Workspace Policies Examples:
- `WorkspacePolicy.get(workspace_id)` - For read/update operations
- `WorkspacePolicy.create(actor)` - For workspace creation
- `WorkspacePolicy.delete(actor)` - For workspace deletion
- `WorkspacePolicy.list_workspaces_me(actor)` - For listing user workspaces

Pattern usage:
```python
await authorize(current_user, WorkspacePolicy.get(workspace_id))
```

### S3 and Files Context

Getting Storage Client:
```python
from extralit_server.contexts import files

# Get appropriate client (Minio or LocalFileStorage)
client = files.get_minio_client()
if client is None:
    raise HTTPException(status_code=500, detail="Storage client not available")
```

File Operations:
```python
# List objects
files.list_objects(client, bucket_name, prefix="schemas/", include_version=False)

# Get object
files.get_object(client, bucket_name, object_path, version_id=None)

# Put object
files.put_object(client, bucket_name, object_path, data, content_type="application/json")
```


## Core Concepts Implementation

### Workspaces and Datasets

As described in the [core concepts documentation](https://docs.extralit.ai/latest/user_guide/core_concepts/), workspaces serve as high-level containers for organizing extraction projects, while datasets represent collections of documents and their associated extracted data.

Implementation:
- Workspace management is handled in `contexts/accounts.py`
- Dataset operations are implemented in `contexts/datasets.py`
- The database models for these entities are defined in `models/database.py`

### Schemas and References

Schemas define the structure and format of data to be extracted, while references uniquely identify scientific papers in the system.

Implementation:
- Schema definitions are handled in `extralit/src/extralit/schema/`
- The system uses Pandera for schema validation
- References are managed through `extralit/src/extralit/schema/references/`


### Data Aggregation and Normalization Architecture

Extralit uses a normalized database approach for storing and presenting extracted data. Each document's extractions are split into separate records (like database tables) with reference keys connecting them, similar to a relational database schema.

#### Document Data Extraction Flow

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
   - Defines structure of Argilla datasets to store normalized records
   - `create_papers_dataset()` configures datasets for document-level records
   - `create_extraction_dataset()` configures datasets for schema-level records


## Common Development Tasks

### Environment Configuration
- Development environment variables are in `extralit-server/.env.dev`
- Test environment uses temporary databases
- Database paths use `${HOME}/.extralit/` pattern in development

### Adding a new API endpoint

1. Define the request/response schemas in `api/schemas/`
2. Implement the handler in `api/handlers/`
3. Add the route to `api/routes.py`
4. Implement the business logic in the appropriate context
5. Add tests in `tests/unit/api/handlers/`

### Modifying database models

1. Update the model in `models/database.py`
2. Create a migration using Alembic:
   ```bash
   cd extralit-server
   pdm run revision -m "description of change"
   ```
3. Update related schemas and validators
4. Test the changes thoroughly

#### Database Migration Guidelines
- Database migrations are automatically configured via environment variables:
  - Dev: `${HOME}/.extralit/extralit-dev.db`
  - Test: Uses temporary databases managed by pytest
- Use `pdm run alembic -c src/extralit_server/alembic.ini check` to verify migration state
- Always test both upgrade and downgrade paths

### Adding frontend functionality

1. Implement domain entities in `v1/domain/entities/`
2. Create or update components in `components/features/`
3. Connect to the backend using services in `v1/infrastructure/services/`
4. Add tests for the new functionality

### Working with Schema and Data Models

1. Define schema in `extralit/src/extralit/extraction/models/schema.py`
2. Implement extraction logic in `extralit/src/extralit/extraction/models/paper.py`
3. Define dataset structure in `extralit/src/extralit/pipeline/export/dataset.py`
4. Create records using functions in `extralit/src/extralit/pipeline/export/record.py`

## Data Aggregation and Annotation Workflow

This section describes how extracted data from documents is structured, stored, and presented to the user for annotation. Extralit uses a relational database approach where data is split into different tables and linked through reference keys.

### 1. The `PaperExtraction` Model

- Core container for document extractions (`extralit/src/extralit/extraction/models/paper.py`)
- Holds multiple pandas DataFrames keyed by schema name
- Contains `SchemaStructure` (`extralit/src/extralit/extraction/models/schema.py`) that defines organization of schemas

### 2. Data Normalization into Argilla Records

Data from `PaperExtraction` is normalized into multiple `rg.Record` objects in Argilla datasets, separating document metadata from specific extractions:

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

- **Table Display**: (`argilla-frontend/components/base/base-render-table/useSchemaTableViewModel.ts`)
  - Manages display and validation of individual tables
  - Identifies primary keys and reference columns
  - Configures table grouping based on references

- **Reference Resolution**: (`argilla-frontend/components/base/base-render-table/useReferenceTablesViewModel.ts`)
  - Identifies reference columns (`_ref` or `_ID` suffix)
  - Dynamically fetches related records from other tables
  - Joins data to create a unified table view for the annotator
  - Manages reference values and combinations for relationships

### 4. Dataset Configuration

- Dataset structure defined in `extralit/src/extralit/pipeline/export/dataset.py`
- `create_papers_dataset()` configures document-level metadata datasets
- `create_extraction_dataset()` configures schema-specific extraction datasets
- Each dataset includes proper field definitions, questions, and metadata properties


Keep the documentation synchronized with the actual implementation to ensure accurate guidance for future development and maintenance.
