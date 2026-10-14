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

### `Can't locate revision identified by 'c1510e93882a'`

The v2→v1 fold rewrote migration history: four revisions that are live on `develop`
(`9f3010c649c8`, `8136bc88ee3a`, `6393b1a01aa0`, `c1510e93882a`) were deleted. A database
migrated before that branch points `alembic_version` at a revision that no longer exists,
so `upgrade head` and `downgrade` both fail. Extralit is pre-production, so the fix is to
rebuild rather than migrate:

```bash
rm -f ~/.extralit/extralit.db            # SQLite (default when EXTRALIT_DATABASE_URL is unset)
dropdb extralit && createdb extralit     # Postgres
uv run alembic -c src/extralit_server/alembic.ini upgrade head
```

This also clears the six orphaned v2 tables (`schemas`, `schema_versions`, `v2_records`,
`v2_questions`, `v2_responses`, `v2_suggestions`) and their enum types, which no migration
drops any more. To keep an existing database instead, see the recovery notes in
`alembic/versions/13da2d87e660_add_schema_versions_and_record_reference.py`.

**Note on `EXTRALIT_DATABASE_URL`:** `.env` and `.env.test` are *not* auto-loaded. With the
variable unset, `settings.database_url` resolves to `sqlite+aiosqlite:///~/.extralit/extralit.db`
— that is what `pytest` and `alembic` actually use here, not the values in those files.

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
