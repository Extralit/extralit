# Extralit Monorepo Project

## Architecture Notes
- **extralit-server/**: FastAPI + PostgreSQL + Redis Queue
- **extralit-frontend/**: Vue 3 / Nuxt 4 (Vite); Pinia state management
- **extralit/**: Python SDK client
- **extralit-hf-space/**: Self-contained HF Spaces deployment bundle (Docker; bundles Elasticsearch + Redis + OCR) — git submodule
- **Vector DB**: Elasticsearch/OpenSearch (migrating to Lancedb)

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

## Deployment and Branching

| Ref | Role | Deploys to |
|---|---|---|
| `main` | trunk; every merged PR | `extralit-dev/develop` (dev HF Space) |
| `release` | long-lived production pointer, moved only by `release.yml` | `extralit/public-demo` |
| `vX.Y.Z` tag | the release itself | PyPI, versioned docs, GitHub Release |
| PR (non-fork) | preview | ephemeral `extralit-dev/pr-N` |

**Never push to `release` or create tags by hand.** Releases are one dispatch:

```bash
gh workflow run release.yml -f version=X.Y.Z                    # dry run (the default)
gh workflow run release.yml -f version=X.Y.Z -f dry_run=false   # cut it
```

That stamps the version via `scripts/bump_version.py` and pushes `main`, `release`, and the
tag atomically. The version lives in three files — always change it with
`python scripts/bump_version.py set --version X.Y.Z`, never by hand.

See `docs/architecture/deployment.md` for the full pipeline

## Gotchas & Rules
- **Check the library before writing a helper.** Before adding any function that renders, serializes, parses or walks a `DoclingDocument`, or splits chunks or fuses scores, check `docling_core.transforms.serializer.*` / `DocItem.export_to_*`, chonkie, and the DuckDB `lance` extension first. Phase 1 of retrieval shipped a `<thead>` serializer, a caption geometry join and a label→markdown CASE that docling already did; all were deleted. Functions with one consumer get inlined.
