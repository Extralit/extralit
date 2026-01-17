# AGENTS.md - Project Setup Instructions

## Component-Specific Setup

Each component has its own AGENTS.md with setup details:
- **extralit-server/AGENTS.md** - Backend server setup
- **extralit-frontend/AGENTS.md** - Frontend UI setup
- **extralit/AGENTS.md** - Python SDK setup

## Prerequisites

- Python 3.10+ (server) / 3.9+ (SDK)
- Node.js 18+
- Docker & Docker Compose (for full stack)
- PDM (Python package manager)

## Quick Setup

```bash
# Install PDM
pip install pdm

# Setup all components
cd extralit-server && pdm install -G test
cd ../extralit && pdm install -e ".[dev]"
cd ../extralit-frontend && npm install

# Run migrations
cd extralit-server && pdm run migrate

# Start services (requires Docker)
docker-compose up -d
```

## Development Workflow

### Running Services
```bash
cd extralit-server && pdm run server-dev  # Server + worker
cd extralit-frontend && npm run dev        # Frontend
```

### Testing
```bash
cd extralit-server && pdm run test         # Server tests
cd extralit && pdm run test                # SDK tests
cd extralit-frontend && npm run test       # Frontend tests
```

### Code Quality
```bash
pdm run lint              # Python linting (ruff)
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

## Issue Tracking

Use **bd** (beads) for work management:

```bash
bd ready                              # Find available work
bd show <id>                          # View details
bd update <id> --status in_progress   # Claim work
bd close <id>                         # Mark complete
bd sync                               # Sync with git
```

## Session Completion Checklist

Before ending ANY session:

1. File issues for remaining work
2. Run quality gates (tests, linters if code changed)
3. Update issue status
4. **PUSH TO REMOTE** (MANDATORY):
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # Verify "up to date with origin"
   ```
5. Clean up (stashes, branches)
6. Verify all changes pushed
7. Provide handoff context

**CRITICAL**: Work is NOT complete until `git push` succeeds. Never stop before pushing.

