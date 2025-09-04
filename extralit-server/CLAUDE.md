# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Extralit-server is the FastAPI backend component of the Extralit ecosystem for scientific literature data extraction with human-in-the-loop workflows. This server handles:

- **User Management**: Authentication, authorization, workspaces, and role-based access
- **Dataset Management**: Scientific literature datasets with metadata, fields, and questions
- **Record Processing**: Document records with responses, suggestions, and annotations
- **Background Jobs**: Asynchronous document processing, OCR, and ML inference via Redis Queue (rq)
- **Vector Search**: Integration with Elasticsearch/OpenSearch for semantic similarity searches
- **Webhook System**: Event notifications and external integrations
- **File Storage**: Document management with S3 S3-compatible storage

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
EXTRALIT_S3_ENDPOINT=http://localhost:9000              # S3/S3 storage
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
- File storage integrates with S3 for scalable object storage