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
