# GitHub Actions Workflows

This directory contains GitHub Actions workflows for building, testing, and deploying the Extralit project. The workflows are designed to run on various events, such as pushes to specific branches, pull requests, and manual triggers.

## Key Workflows

### `argilla.yml`

Builds and publishes the `argilla` SDK Python package.

- **Trigger**: Push to main/develop/releases branches, pull requests, or manual dispatch
- **Python versions**: 3.9, 3.10, 3.11, 3.12, 3.13
- **Key steps**:
  - Build and test the package
  - Upload test coverage to Codecov
  - Publish to PyPI

#### Python 3.13 Compatibility

Python 3.13 support requires special handling due to some dependencies not yet being fully compatible:

- The `spacy` dependency is specified with version conditions based on the Python version (v3.8.0+ for Python 3.13)
- These conditional dependencies ensure the package can be built and tested on Python 3.13

### `argilla-server.yml`

Builds and publishes the `argilla-server` package.

- **Trigger**: Push to main/develop/releases branches, pull requests, or manual dispatch
- **Key steps**:
  - Run Elasticsearch, PostgreSQL, Redis, and MinIO services
  - Build and test the server package
  - Build Docker images
  - Publish to PyPI
- **Frontend integration**: Includes steps to build the frontend and incorporate it into the server package

## Caching Strategy

The workflows use multiple caching strategies to improve build performance:

1. **PDM cache**: Through the `setup-pdm` action
2. **UV cache**: Through the `actions/cache` action
   - Key format: `{os}-uv-{python-version}-{pdm_hash}` for argilla
   - Key format: `{os}-uv-server-{pdm_hash}` for argilla-server
   - Paths cached: `~/.cache/uv`, `~/.cache/pip`

The UV cache uses the PDM lockfile hash to ensure the cache is invalidated when dependencies change. This approach provides more precise cache invalidation than date-based keys.

## Environment Variables

The workflows set various environment variables:

- `UV_CACHE_DIR`: Location of the UV cache
- `UV_NO_WAIT`: Prevent UV from waiting for operations to complete (improves CI performance)
- `UV_SYSTEM_PYTHON`: Use the system Python instead of a virtual environment
- `PDM_IGNORE_ACTIVE_VENV`: Ignore active virtual environments

Additional environment variables are set in specific workflows:
- For `argilla-server.yml`: Database connection variables for Postgres, Elasticsearch, Redis, and MinIO
- For `argilla.yml`: HuggingFace credentials for integration tests

## Common Issues & Solutions

### Package caching not working

If dependencies are still being downloaded despite cache hits:

1. Ensure `pdm.lock` is up-to-date with `pyproject.toml` (run `pdm lock --no-sync`)
2. Make sure the `pdm.lock` file is committed to the repository (not gitignored)
3. Check that the cache key properly includes the lockfile hash
4. Verify that both directories (`~/.cache/uv` and `~/.cache/pip`) are being cached

### Incompatible dependencies

For Python 3.13 or newer Python versions:

1. Use conditional dependencies in `pyproject.toml` with version specifiers
2. Add special handling in workflows for these Python versions
3. Skip tests that depend on incompatible packages

## Best Practices

1. Always commit the `pdm.lock` file to ensure reproducible builds
2. Use conditional dependencies for Python version compatibility
3. Use caching effectively with proper invalidation strategies
4. Set up proper test coverage reporting