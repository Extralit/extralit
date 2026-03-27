# extralit-server Setup

## Installation

```bash
cd extralit-server/

# Install dependencies
uv sync
```

## Development

```bash
uv run python -m extralit_server server-dev    # Start server + worker with auto-reload
uv run python -m extralit_server server        # Server only
uv run python -m extralit_server worker        # Worker only
uv run alembic -c src/extralit_server/alembic.ini upgrade head  # Run database migrations
```

## Testing

```bash
uv run pytest tests --disable-warnings                         # Run all tests
uv run pytest tests --disable-warnings --cov=extralit_server   # Run tests with coverage
uv run ruff check                                              # Ruff linting
```

**Note**: Full test suite requires CI environment (Elasticsearch, PostgreSQL, Redis, MinIO). Some tests will skip locally.

## Database

- **Migrations**: Always use Alembic
  - `uv run alembic -c src/extralit_server/alembic.ini revision --autogenerate -m "description"` - Create migration after model changes
  - `uv run alembic -c src/extralit_server/alembic.ini upgrade head` - Apply migrations
- **PostgreSQL** required for development
- Run migrations before starting development

## Key Technologies

- FastAPI + SQLAlchemy ORM
- Redis Queue (background jobs)
- OAuth2 + JWT authentication
- Alembic migrations
- Pytest (async support, factory-boy fixtures)

## Structure

```
src/extralit_server/
  /api         # FastAPI endpoints
  /models      # SQLAlchemy models
  /auth        # Authentication
  /tasks       # Background jobs
  /alembic     # Database migrations
```

## Environment

See `.github/workflows/copilot-setup-steps.yml` for complete CI setup steps.
