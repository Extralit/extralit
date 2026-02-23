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

# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

