---
inclusion: always
---

# Technology Stack & Development Guidelines

## Architecture Overview
Extralit is a monorepo with 3 main packages:
- **extralit-server/**: FastAPI backend with PostgreSQL/SQLAlchemy
- **extralit-frontend/**: Nuxt.js 2.17 (Vue.js 2.7) web UI
- **extralit/**: Python SDK and CLI

## Code Style & Conventions

### Python (Backend & SDK)
- **Naming**: snake_case for files, modules, functions, variables
- **Type Hints**: Always use type hints with Pydantic models
- **Async/Await**: Use async patterns for database and external API calls
- **Error Handling**: Use custom exceptions from `_exceptions` modules
- **Database**: SQLAlchemy 2.0 async patterns, Alembic migrations
- **API**: FastAPI with Pydantic schemas, dependency injection
- **Build**: PDM for dependency management, not pip

### Frontend (Vue.js/Nuxt.js)
- **Naming**: PascalCase for components, camelCase for methods/props
- **Components**: Auto-imported from `~/components` directory
- **TypeScript**: Use `<script lang="ts">` for all new components
- **View Models**: Separate business logic into `useViewModelName.ts` files
- **Dependency Injection**: Use `useResolve` from `ts-injecty`
- **API Calls**: Use `@nuxt/axios` with `{proxy: true, browserBaseURL: "api"}`
- **Styling**: SCSS with component-scoped styles, avoid inline styles
- **Testing**: Jest for unit tests, Playwright for e2e

### File Structure Patterns
- **Backend API**: `api/handlers/v1/resource_name.py` for endpoints
- **Frontend Components**: `components/base/` for reusable, `components/features/` for specific
- **Business Logic**: `contexts/` (backend) or `v1/domain/usecases/` (frontend)
- **Database Models**: `models/database.py` with SQLAlchemy declarative models

## Development Rules

### Backend Development
- Use PDM, not pip: `pdm install`, `pdm run server-dev`
- Database changes require Alembic migrations
- Background jobs go in `jobs/` directory with RQ
- API versioning: all endpoints under `/api/v1/`
- Authentication: JWT tokens with OAuth2 flows

### Frontend Development
- No new README files for components unless specifically requested
- Skip unit tests unless explicitly asked
- Use existing base components before creating new ones
- Follow Vue.js 2.7 Composition API patterns
- Internationalization: Use Vue i18n with translation files

### Testing Patterns
- **Jest Mocks**: Define inline to avoid hoisting issues
- **Component Tests**: Use stubs for base components
- **View Model Tests**: Test public interface, not implementation
- **Mock Setup**: Configure in `beforeEach`, clean in `afterEach`

## Key Technologies
- **Backend**: FastAPI 0.115+, SQLAlchemy 2.0, Pydantic 2.9, Redis/RQ
- **Frontend**: Nuxt.js 2.17, Vue.js 2.7, TypeScript, Pinia, Axios
- **Database**: PostgreSQL (prod), SQLite (dev/test)
- **Search**: ElasticSearch 8.x or OpenSearch 2.x
- **Build**: PDM (Python), npm (Frontend)

## Development Commands

### Backend (extralit-server/)
```bash
pdm install                    # Install dependencies
pdm run migrate               # Run database migrations
pdm run server-dev            # Start dev server with auto-reload
pdm run test                  # Run tests
pdm run worker                # Start background worker
```

### Frontend (extralit-frontend/)
```bash
npm install                   # Install dependencies
npm run dev                   # Start dev server
npm run build                 # Production build
npm run test                  # Run Jest unit tests
npm run e2e                   # Run Playwright e2e tests
```

### SDK (extralit/)
```bash
pdm install                   # Install dependencies
pdm run test                  # Run tests
extralit --help               # CLI usage
```

### Full Stack
```bash
docker-compose up             # Start all services
tilt up                       # Kubernetes development (if configured)
```

## Architecture Patterns

### Backend Patterns
- **API Structure**: `/api/v1/` prefix, resource-based endpoints
- **Database**: Async SQLAlchemy with dependency injection
- **Background Jobs**: Redis Queue (RQ) for async processing
- **Error Handling**: Custom exceptions with proper HTTP status codes
- **Authentication**: JWT with OAuth2, role-based access control

### Frontend Patterns
- **Component Architecture**: Base components + feature-specific components
- **State Management**: Pinia stores with TypeScript
- **API Integration**: Axios with proxy configuration
- **Routing**: File-based routing with Nuxt.js conventions
- **Styling**: SCSS modules with BEM-like naming

### Data Flow
- **Client → Server**: REST API with JSON payloads
- **Server → Database**: SQLAlchemy ORM with async patterns
- **Server → Search**: ElasticSearch for full-text search
- **Background Processing**: Redis Queue for heavy operations

## Environment Configuration
- **Database**: `EXTRALIT_DATABASE_URL` (PostgreSQL/SQLite)
- **Search**: `EXTRALIT_ELASTICSEARCH` (ElasticSearch/OpenSearch)
- **Cache**: `EXTRALIT_REDIS_URL` (Redis for jobs/cache)
- **Frontend**: `API_BASE_URL` (backend API endpoint)
- **AI**: `OPENAI_API_KEY` (LLM integration)
- **Storage**: `S3_*` variables (object storage)