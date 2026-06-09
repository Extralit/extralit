# Extralit Monorepo Project

## Component-Specific Setup

Each component has its own `CLAUDE.md` with setup details:
- **extralit-server/CLAUDE.md** - Backend server setup
- **extralit-frontend/CLAUDE.md** - Frontend UI setup
- **extralit/CLAUDE.md** - Python SDK setup

## Prerequisites

- Python 3.10+ (server) / 3.9+ (SDK)
- Node.js 18+
- Docker & Docker Compose (for full stack)
- uv (Python package manager)

## Quick Setup

```bash
# Install uv
pip install uv

# Setup all components
cd extralit-server && uv sync --dev
cd ../extralit && uv sync
cd ../extralit-frontend && npm install

# Run migrations
cd extralit-server && uv run alembic -c src/extralit_server/alembic.ini upgrade head

# Start services (requires Docker)
docker-compose up -d
```

## Development Workflow

### Running Services
```bash
cd extralit-server && uv run python -m extralit_server server-dev  # Server + worker
cd extralit-frontend && npm run dev        # Frontend
```

### Testing
```bash
cd extralit-server && uv run pytest tests  # Server tests
cd extralit && uv run pytest tests         # SDK tests
cd extralit-frontend && npm run test       # Frontend tests
```

### Code Quality
```bash
uv run ruff check         # Python linting (ruff)
npm run lint              # Frontend linting (ESLint)
npm run format            # Frontend formatting (Prettier)
```

## Architecture Notes

- **extralit-server/**: FastAPI + PostgreSQL + Redis Queue
- **extralit-frontend/**: Vue.js/Nuxt.js (Vuex → Pinia migration)
- **extralit/**: Python SDK client
- **Vector DB**: Elasticsearch/OpenSearch (separate service)

### Key Patterns
- Backend: SQLAlchemy ORM, Alembic migrations, async pytest
- Frontend: Domain-driven design, dependency injection
- Database: Always use Alembic for schema changes
