# extralit SDK Setup

## Installation

```bash
cd extralit/

# Install in development mode
pip install -e ".[dev]"

# Or use PDM
pdm install -e ".[dev]"
```

## Development

```bash
pdm run test          # Run all tests
pdm run test-cov      # Run tests with coverage
pdm run lint          # Ruff linting
pdm run all           # Format, lint, and test
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
