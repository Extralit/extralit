# Extralit Codebase Organization Guide

This guide provides an overview of the Extralit codebase architecture to help new contributors understand how the project is organized. Extralit is a monorepo containing multiple interconnected components that work together to provide document extraction, processing, and annotation capabilities.

## Repository Structure

Extralit is organized as a monorepo with several main components:

- **argilla**: Python SDK and core extraction functionality
- **argilla-server**: Backend server implementation
- **argilla-frontend**: Frontend web application
- **argilla-v1**: Legacy compatibility layer
- **examples**: Sample implementations and deployment configurations

## Core Components

### Frontend (`argilla-frontend`)

The frontend is built with Vue.js and Nuxt.js, providing a modern web interface for document management, extraction, and annotation.

Key directories:
- `components/`: UI components organized by functionality
  - `base/`: Reusable UI components (buttons, inputs, modals, etc.)
  - `features/`: Feature-specific components (annotation, dataset creation, etc.)
- `pages/`: Application routes and page components
- `v1/domain/`: Core domain entities and business logic
- `plugins/`: Vue.js plugins and extensions
- `assets/`: Static assets like styles, fonts, and images

### Backend Server (`argilla-server/src/argilla_server`)

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

### SDK and Core Extraction (`argilla/src/extralit`)

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

The system uses SQLAlchemy for database operations with models defined in `argilla-server/src/argilla_server/models/database.py`. These models represent the core entities in the system:
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
- Schema definitions are handled in `argilla/src/extralit/schema/`
- The system uses Pandera for schema validation
- References are managed through `argilla/src/extralit/schema/references/`

### Data Extraction Workflow

The extraction workflow involves document import, OCR, schema application, LLM-assisted extraction, review, and export.

Implementation:
- Document import is handled in `contexts/files.py`
- OCR and text extraction is implemented in `extralit/preprocessing/`
- LLM-assisted extraction is in `extralit/extraction/`
- Review functionality is provided through the frontend components
- Export capabilities are in `extralit/pipeline/export/`

## Development Workflow

When contributing to Extralit, consider these guidelines:

1. **Understand the context**: Identify which domain context your change belongs to
2. **Follow existing patterns**: Look at similar implementations for guidance
3. **Maintain separation of concerns**:
   - Keep API handlers thin, delegating to contexts for business logic
   - Keep database models focused on structure, not behavior
   - Use validators for input validation
4. **Write tests**: Add tests for new functionality in the appropriate test directories
5. **Document your changes**: Update documentation when adding or changing features

## Common Development Tasks

### Adding a new API endpoint

1. Define the request/response schemas in `api/schemas/`
2. Implement the handler in `api/handlers/`
3. Add the route to `api/routes.py`
4. Implement the business logic in the appropriate context
5. Add tests in `tests/unit/api/handlers/`

### Modifying database models

1. Update the model in `models/database.py`
2. Create a migration using Alembic
3. Update related schemas and validators
4. Test the changes thoroughly

### Adding frontend functionality

1. Implement domain entities in `v1/domain/entities/`
2. Create or update components in `components/features/`
3. Connect to the backend using services in `v1/infrastructure/services/`
4. Add tests for the new functionality

