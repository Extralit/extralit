# extralit SDK Setup

## Installation

```bash
cd extralit/

# Install in development mode
uv sync
```

## Development

```bash
uv run pytest tests --disable-warnings                # Run all tests
uv run pytest tests --disable-warnings --cov=extralit  # Run tests with coverage
uv run ruff check                                      # Ruff linting
uv run ruff format                                     # Ruff formatting
```

## Requirements

- Python 3.9+
- Used for programmatic interaction with extralit-server

## Usage

```python
import extralit as ex

client = ex.Extralit(
    api_url="https://your-deployment-url",
    api_key="your-api-key"
)
```

## Testing

- pytest with standard fixtures
- Tests run independently without external services

## Structure

```
src/extralit/
  /client      # API client
  /models      # Data models
  /utils       # Utilities
```

## v2 SDK (`src/extralit/v2/`)

- Parallel package for `/api/v2` (schema-centric). Import wall: v2 imports nothing from v1
  except `extralit.client.login`; only `cli/app.py` imports v2 (composition root).
- Wire types are GENERATED: `_api/openapi.json` (server `openapi-dump` snapshot) ->
  `_api/_generated.py` via datamodel-codegen. Never hand-edit; regenerate with the command
  in `tests/unit/v2/test_contract.py` and keep both in sync (drift-gated).
- `AsyncClient` is the real client; `Client` is a mechanical sync facade (background-thread
  portal — works in Jupyter). CLI verbs register at TOP level (`extralit schemas|records|...`),
  JSON-first (`--json` or non-TTY), errors as JSON on stderr (exit 0/1/2/3).
