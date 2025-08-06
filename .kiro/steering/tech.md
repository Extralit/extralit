# Technology Stack

## Architecture Overview
Extralit is a multi-component system with 5 core components:
- **Python SDK**: Client library (`pip install extralit`)
- **FastAPI Server**: Backend API handling users, storage, and data management
- **Web UI**: Vue.js/Nuxt.js frontend for data visualization and annotation
- **Vector Database**: ElasticSearch or AWS OpenSearch for scalable search
- **Database**: PostgreSQL for application data storage

## Backend (extralit-server/)
- **Framework**: FastAPI ~0.115.0
- **Database**: SQLAlchemy 2.0 with PostgreSQL (asyncpg) or SQLite (aiosqlite)
- **Search**: ElasticSearch 8.x or OpenSearch 2.x
- **Background Jobs**: Redis Queue (RQ) with Redis
- **Authentication**: python-jose with JWT tokens, OAuth2 support
- **Build System**: PDM (Python Dependency Management)
- **Python**: >=3.9

### Key Dependencies
- Pydantic 2.9 for data validation
- Alembic for database migrations
- Uvicorn for ASGI server
- Typer for CLI interface

## Frontend (extralit-frontend/)
- **Framework**: Nuxt.js 2.17 (Vue.js 2.7)
- **Component Import**: Nuxt automatically scans the ~/components directory and makes all .vue files
- **Build System**: npm/yarn
- **UI Components**: Custom component library with SCSS
- **State Management**: Pinia + Vuex
- **Testing**: Jest (unit), Playwright (e2e)
- **Node**: >=18.16.1
- **TypeScript**: Use `<script lang="ts">` for Vue.js TypeScript support
- **Linting**: ESLint + Prettier (already in pre-commit hook)
- **README and Tests**: Skip creating new README and tests for each page or component unless asked to

### Key Dependencies
- TypeScript support
- Axios for HTTP client
- TipTap for rich text editing
- Tabulator for data tables
- Vue i18n for internationalization

## Client SDK (extralit/)
- **Framework**: Python SDK with CLI (Typer)
- **Build System**: PDM
- **Key Features**: Document processing, LLM integration, vector storage
- **Dependencies**: LlamaIndex, Weaviate, spaCy, pandas

## Common Commands

### Backend Development
```bash
cd extralit-server
pdm install
pdm run migrate          # Run database migrations
pdm run server-dev       # Start dev server with auto-reload
pdm run test            # Run tests
pdm run worker          # Start background worker
```

### Frontend Development
```bash
cd extralit-frontend
npm install
npm run dev             # Start dev server
npm run build           # Production build
npm run test            # Run unit tests
npm run e2e             # Run e2e tests
```

### Client SDK Development
```bash
cd extralit
pdm install
pdm run test            # Run tests
extralit --help         # CLI usage
```

### Docker Development
```bash
docker-compose up       # Start full stack
pdm run docker-build-extralit-server  # Build server image
```

### Kubernetes Development (Tilt)
```bash
tilt up                 # Start k8s development environment
tilt down               # Stop k8s environment
```

## Environment Variables
- `EXTRALIT_DATABASE_URL`: Database connection string
- `EXTRALIT_ELASTICSEARCH`: ElasticSearch URL
- `EXTRALIT_REDIS_URL`: Redis connection for background jobs
- `API_BASE_URL`: Backend API URL for frontend
- `OPENAI_API_KEY`: For LLM integration
- `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`: Object storage