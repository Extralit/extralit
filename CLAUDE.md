# Extralit Monorepo Project

## Architecture Notes
- **extralit-server/**: FastAPI + PostgreSQL + Redis Queue
- **extralit-frontend/**: Vue 3 / Nuxt 4 (Vite); Pinia state management
- **extralit/**: Python SDK client
- **extralit-hf-space/**: Self-contained HF Spaces deployment bundle (Docker; bundles Elasticsearch + Redis + OCR) — git submodule
- **Vector DB**: Elasticsearch/OpenSearch (separate service)

### Key Patterns
- Backend: SQLAlchemy ORM, Alembic migrations, async pytest
- Frontend: Domain-driven design, dependency injection
- Database: Always use Alembic for schema changes

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

# Python Package Management with uv
Use uv exclusively for Python package management in this project.

## Package Management Commands
- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:
- Install dependencies: `uv add <package>`, avoid adding to pyproject.toml directly
- Remove dependencies: `uv remove <package>`
- Sync environment: `uv sync`
- Lock dependencies: `uv lock`

## Running Python Code
- Run a Python script with `uv run <script-name>.py`
- Run Python tools with `uv run <tool>` (e.g. `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run ty check`, `uv run pre-commit`, `npm run lint`, `npm run format`)
- Launch a Python REPL with `uv run python`

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

## Branching

Trunk-based. **`main` is the trunk and the default branch** — every change, code or docs,
branches from `main` and squash-merges back via PR. There is no `develop` branch and no
`releases/**` branches.

| Ref | Role | Deploys to |
|---|---|---|
| `main` | trunk; every merged PR | `extralit-dev/develop` (dev HF Space) |
| `release` | long-lived production pointer, moved only by `release.yml` | `extralit/public-demo` |
| `vX.Y.Z` tag | the release itself | PyPI, versioned docs, GitHub Release |
| PR | preview | ephemeral `extralit-dev/pr-N` |

Branch names: `feat/*`, `fix/*`, `docs/*`, short-lived. PR titles use the matching
`feat:` / `fix:` / `docs:` / `chore:` prefix — release notes are generated from them.

**Never push to `release` or create tags by hand.** Releases are one dispatch:

```bash
gh workflow run release.yml -f version=X.Y.Z                    # dry run (the default)
gh workflow run release.yml -f version=X.Y.Z -f dry_run=false   # cut it
```

That stamps the version via `scripts/bump_version.py` and pushes `main`, `release`, and the
tag atomically. The version lives in three files — always change it with
`python scripts/bump_version.py set --version X.Y.Z`, never by hand.

See `docs/architecture/deployment.md` for the full pipeline and
`extralit/docs/community/release_guide.md` for the release runbook.

## Git Workgrees
When creating a git workgree, place it at `.worktree/<branch-name>` relative to the repo root, normalizing `/` to `-` in the branch-name.

Example: branch `feature/add-new-feature` should be placed at `.worktree/feature-add-new-feature`.
