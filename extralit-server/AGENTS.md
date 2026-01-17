# extralit-server Setup

## Installation

```bash
cd extralit-server/

# Install PDM if needed
pip install pdm

# Configure PDM to use uv
pdm config use_uv true

# Install dependencies
pdm install -G test
```

## Development

```bash
pdm run server-dev    # Start server + worker with auto-reload
pdm run server        # Server only
pdm run worker        # Worker only
pdm run migrate       # Run database migrations
```

## Testing

```bash
pdm run test          # Run all tests
pdm run test-cov      # Run tests with coverage
pdm run lint          # Ruff linting
```

**Note**: Full test suite requires CI environment (Elasticsearch, PostgreSQL, Redis, MinIO). Some tests will skip locally.

## Database

- **Migrations**: Always use Alembic
  - `pdm run revision -m "description"` - Create migration after model changes
  - `pdm run migrate` - Apply migrations
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
