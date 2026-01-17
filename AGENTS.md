# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Extralit is a multi-component system for scientific literature data extraction with human-in-the-loop workflows:

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

