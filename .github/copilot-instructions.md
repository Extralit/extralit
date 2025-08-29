# Extralit Architecture Overview

Extralit (https://github.com/Extralit/extralit) is a multi-component system for scientific literature data extraction with human-in-the-loop workflows:

- **extralit-server/**: FastAPI backend server with PostgreSQL database, handles users, datasets, records, and API interactions
- **extralit-frontend/**: Vue.js/Nuxt.js web UI for data visualization, annotation, and team collaboration
- **extralit/**: Python SDK client library for programmatic interaction with the server
- **Vector Database**: External Elasticsearch/OpenSearch for scalable vector similarity searches

## Development Commands

### Server (extralit-server/)
```bash
cd extralit-server/
pdm run server-dev        # Start server with auto-reload + worker
pdm run server           # Start server only
pdm run worker           # Start background worker only
pdm run migrate          # Run database migrations
pdm run test             # Run tests
pdm run test-cov         # Run tests with coverage
pdm run lint             # Run ruff linting
```

### Frontend (extralit-frontend/)
```bash
cd extralit-frontend/
npm run dev              # Development server
npm run build            # Production build
npm run test             # Run Jest tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage report
npm run e2e              # Run Playwright e2e tests (interactive UI)
npm run e2e:silent       # Run e2e tests in headless mode
npm run e2e:report       # Show Playwright test report
npm run lint             # ESLint check
npm run lint:fix         # Fix ESLint issues
npm run format           # Format with Prettier
npm run format:check     # Check formatting without modifying files
npm run generate-icons   # Generate icon components from SVG files
```

### Client SDK (extralit/)
```bash
cd extralit/
pdm run test             # Run tests
pdm run test-cov         # Run tests with coverage
pdm run lint             # Run ruff linting
pdm run format           # Format with black
pdm run all              # Format, lint, and test
```

## Key Development Notes

### Frontend Architecture
- Transitioning from Vuex to Pinia (v1/ directory contains new architecture)
- Uses domain-driven design with entities, use cases, and dependency injection
- Component structure: base (stateless) → features (page-specific) → global (reusable)

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
- Frontend: ESLint + Prettier with TypeScript support
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

### Testing and Quality
```bash
pdm run test             # Run pytest with warnings disabled
pdm run test-cov         # Run tests with coverage reporting
pdm run lint             # Run ruff linting
pdm run format           # Format code with black
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

# `extralit-frontend` Frontend Architecture Overview

Extralit frontend is a Vue.js/Nuxt.js web application for scientific literature data extraction and annotation with human-in-the-loop workflows.

**Tech Stack:**
- **Vue 2.7 + Nuxt 2** with Composition API support via `@nuxtjs/composition-api`
- **TypeScript** for type safety
- **SCSS** with design system and component-scoped styles
- **Pinia** for state management (transitioning from Vuex)
- **Domain-Driven Design** with clean architecture principles

## Development Commands

```bash
# Development
npm run dev              # Start development server with hot reload
npm run build            # Production build
npm run start            # Start production server (after build)

# Testing
npm run test             # Run Jest unit tests
npm run test:watch       # Run tests in watch mode
npm run test:coverage    # Run tests with coverage report
npm run e2e              # Run Playwright e2e tests (interactive UI)
npm run e2e:silent       # Run e2e tests in headless mode
npm run e2e:report       # Show Playwright test report

# Code Quality
npm run lint             # ESLint check
npm run lint:fix         # Fix ESLint issues automatically
npm run format           # Format code with Prettier
npm run format:check     # Check formatting without modifying files

# Assets
npm run generate-icons   # Generate icon components from SVG files
```

## Architecture Patterns

### Domain-Driven Design Structure

The `v1/` directory contains the new clean architecture implementation:

```
v1/
├── domain/                    # Business logic layer
│   ├── entities/              # Domain entities and types
│   ├── events/                # Domain events (Event suffix)
│   ├── services/              # Domain service interfaces (I prefix)
│   └── usecases/              # Use case implementations (kebab-case, use-case suffix)
├── infrastructure/            # Technical implementation layer
│   ├── events/                # Event handlers (EventHandler suffix)
│   ├── repositories/          # API repository implementations (Repository suffix)
│   ├── services/              # UI hooks and utilities (use* pattern)
│   ├── storage/               # Client-side storage (Storage suffix)
│   └── types/                 # Infrastructure types and API models
├── di/                        # Dependency injection container
└── store/                     # Pinia stores
```

### Component Architecture

```
components/
├── base/                      # Stateless, reusable UI components
│   ├── base-button/           # BaseButton.vue
│   ├── base-input/            # BaseInput.vue
│   └── base-modal/            # BaseModal.vue, etc.
├── features/                  # Feature-specific components by domain
│   ├── annotation/            # Annotation workflow components
│   ├── dataset-creation/      # Dataset creation components
│   ├── documents/             # Document management components
│   └── user-settings/         # User settings components
└── components/                # Legacy component organization (being phased out)
```

### View Model Pattern

Components use the view model pattern for separation of concerns:

```typescript
// Component setup
export default {
  setup(props) {
    return useComponentNameViewModel(props);
  }
};

// View model composable
export function useComponentNameViewModel(props) {
  // Business logic, API calls, reactive state
  return {
    // Reactive properties and methods for template
  };
}
```

### Dependency Injection

Services are registered in `v1/di/di.ts` using the `ts-injecty` container:

```typescript
// Registration
register(UseCase).withDependency(Repository).build()

// Usage in composables
const useCase = useResolve(UseCase);
```

## Key Development Patterns

### API Communication

- **Repositories**: Handle API communication (`v1/infrastructure/repositories/`)
- **Axios Integration**: Uses `@nuxtjs/axios` with proxy configuration
- **Base URL**: All API calls go through `/api/` proxy to backend
- **Error Handling**: Centralized in `plugins/axios/axios-global-handler.ts`

### State Management

- **Pinia Stores**: New state management in `v1/store/`
- **Storage Services**: Client-side persistence in `v1/infrastructure/storage/`
- **Reactive State**: Using Composition API reactivity

### Component Patterns

- **Base Components**: Stateless, prop-driven components in `components/base/`
- **Feature Components**: Domain-specific components with business logic
- **View Models**: Business logic extracted to composable functions
- **Props & Events**: TypeScript interfaces for component contracts

### Testing Patterns

#### Unit Tests (Jest)

```typescript
// Component testing
import { mount } from '@vue/test-utils';
import Component from './Component.vue';

describe('Component', () => {
  it('should render correctly', () => {
    const wrapper = mount(Component);
    expect(wrapper.exists()).toBe(true);
  });
});
```

Configuration in `jest.config.js`:
- Uses `@vue/vue2-jest` for Vue SFC transformation
- Module aliases for `~` and `@` paths
- JSDOM environment for DOM testing
- Coverage collection from components and pages

#### E2E Tests (Playwright)

```typescript
// Page object model
import { test, expect } from '@playwright/test';

test('annotation workflow', async ({ page }) => {
  await page.goto('/dataset/123');
  await expect(page.locator('[data-testid="record-form"]')).toBeVisible();
});
```

Configuration in `playwright.config.ts`:
- Screenshot comparison for visual regression testing
- API mocking in `e2e/common/` directory
- Page object patterns for reusable test utilities

### Styling Patterns

- **SCSS Architecture**: Organized in `assets/scss/` with abstracts, base, and components
- **Component Scoped**: Use `<style scoped>` for component-specific styles
- **Design System**: Consistent spacing, colors, and typography via SCSS variables
- **Responsive**: Mobile-first approach with mixins in `assets/scss/abstract/mixins/`

### Internationalization

- **i18n**: 4 languages supported (en, de, es, ja) in `translation/` directory
- **Strategy**: No prefix strategy for cleaner URLs
- **Fallback**: English as default fallback language

## Common Development Tasks

### Adding New Components

1. Create component in appropriate `components/` subdirectory
2. Follow naming convention: `ComponentName.vue`
3. Add TypeScript props interface
4. Create view model composable if business logic is needed
5. Add unit tests in same directory

### Creating Use Cases

1. Define interface in `v1/domain/services/`
2. Implement use case in `v1/domain/usecases/`
3. Create repository if API access needed
4. Register dependencies in `v1/di/di.ts`
5. Add unit tests for business logic

### API Integration

1. Define API types in `v1/infrastructure/types/`
2. Create repository in `v1/infrastructure/repositories/`
3. Implement use case consuming repository
4. Register dependencies in DI container
5. Use in view models via `useResolve()`

### Running Tests

- **Unit Tests**: Focus on business logic and component behavior
- **E2E Tests**: Critical user workflows and integration scenarios
- **Coverage**: Aim for high coverage on use cases and view models
- **CI**: Tests run automatically in GitHub Actions

### File Organization

- **Kebab-case**: For directory names (`user-settings/`)
- **PascalCase**: For component files (`UserSettings.vue`)
- **camelCase**: For variables and functions
- **Interfaces**: Prefix with `I` for service interfaces

### Performance Considerations

- **Code Splitting**: Nuxt handles automatic code splitting
- **Lazy Loading**: Use dynamic imports for heavy components
- **Bundle Analysis**: Use `npm run build` with analyze option
- **Image Optimization**: Use appropriate formats and sizes

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


Keep the documentation synchronized with the actual implementation to ensure accurate guidance for future development and maintenance.

## File Upload Components Architecture

The file upload components have been refactored to use Vue 2 + Composition API with shared composables for improved maintainability and code reuse:

### Components Structure:
- **ImportFileUpload.vue**: Orchestrator component that coordinates TableUpload and PdfUpload
- **TableUpload.vue**: Handles bibliography file uploads (BibTeX/CSV) with column selection
- **PdfUpload.vue**: Handles PDF folder uploads with file matching

### Composables:
- **useImportFileUploadViewModel.ts**: Core shared logic with strategy pattern (available for future enhancements)
- **useTableUploadLogic.ts**: Bibliography-specific upload logic
- **usePdfUploadLogic.ts**: PDF-specific upload logic
- **types.ts**: Shared TypeScript interfaces and type definitions

### Benefits Achieved:
- **DRY Principle**: Common drag/drop, error handling, and state management logic extracted
- **Type Safety**: Shared type definitions prevent interface mismatches
- **Better Testing**: Business logic separated from UI concerns, enabling unit testing of composables
- **Maintainability**: Cleaner component structure with logic in composables
- **Backward Compatibility**: Same event contracts and prop interfaces maintained
- **Consistency**: All components now follow Composition API patterns consistent with codebase architecture

All components maintain their existing functionality while now using reactive Composition API patterns for better code organization and reusability.
