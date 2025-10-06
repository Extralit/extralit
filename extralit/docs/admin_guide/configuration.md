# Configuration Management

Extralit Server uses a centralized configuration system based on Pydantic Settings, providing type safety, validation, and clear documentation for all configuration options.

## Overview

Starting from version 2.0, Extralit Server uses a **Pydantic-based settings model** located in `extralit_server.config`. This provides:

- ✅ **Type Safety**: All settings are strongly typed with automatic validation
- ✅ **Documentation**: Every setting includes inline documentation
- ✅ **Validation**: Configuration errors are caught at startup, not runtime
- ✅ **IDE Support**: Autocomplete and type hints in modern IDEs
- ✅ **Secret Management**: Sensitive values are protected using `SecretStr`

## Configuration Sources

Settings are loaded in the following order (later sources override earlier ones):

1. **Default values** defined in the Settings class
2. **Environment variables**
3. **.env file** (if present in the project root)

## Quick Start

### 1. Copy the Example Configuration

```bash
cd extralit-server
cp .env.example .env
```

### 2. Edit Your Configuration

Open `.env` and configure the values for your deployment:

```bash
# Required for production
EXTRALIT_AUTH_SECRET_KEY=your-secret-key-here
EXTRALIT_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/extralit

# Optional but recommended
EXTRALIT_REDIS_URL=redis://localhost:6379/0
```

### 3. Generate a Secret Key

For production deployments, generate a secure secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use this value for `EXTRALIT_AUTH_SECRET_KEY`.

## Configuration Categories

### Authentication & Security

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `EXTRALIT_AUTH_SECRET_KEY` | SecretStr | None | Secret key for JWT token signing ⚠️ **Required for production** |
| `EXTRALIT_LOCAL_AUTH_USERS_DB_FILE` | str | `.users.yml` | Path to local users database file |

!!! warning "Production Security"
    Always set a strong `EXTRALIT_AUTH_SECRET_KEY` in production. Never use default values or commit secrets to version control.

### Database Configuration

Extralit supports both SQLite (for development) and PostgreSQL (for production).

#### SQLite (Development)

```bash
EXTRALIT_DATABASE_URL=sqlite+aiosqlite:///./extralit-dev.db?check_same_thread=False
```

#### PostgreSQL (Production Recommended)

```bash
EXTRALIT_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/extralit
```

### Redis Configuration

Redis is used for caching and background job queues:

```bash
EXTRALIT_REDIS_URL=redis://localhost:6379/0
```

For Redis with authentication:

```bash
EXTRALIT_REDIS_URL=redis://:password@localhost:6379/0
```

### S3-Compatible Storage

Configure S3 or S3-compatible storage (MinIO, DigitalOcean Spaces, AWS S3):

```bash
EXTRALIT_S3_ENDPOINT=http://localhost:9000
EXTRALIT_S3_ACCESS_KEY=your-access-key
EXTRALIT_S3_SECRET_KEY=your-secret-key
EXTRALIT_S3_REGION=us-east-1
EXTRALIT_S3_SECURE=false  # Set to true for HTTPS
```

!!! note "S3 Configuration Validation"
    When using S3 storage, all three required fields (`ENDPOINT`, `ACCESS_KEY`, `SECRET_KEY`) must be set. The configuration will fail validation if any are missing.

### Marker PDF Processing

Marker can run in two modes:

#### Local Mode (Default)

Runs Marker in-process. Requires `marker-pdf` to be installed:

```bash
MARKER_RUN_MODE=local
```

#### Modal Mode (Remote API)

Uses a remote Modal deployment for Marker processing:

```bash
MARKER_RUN_MODE=modal
MARKER_MODAL_BASE_URL=https://your-modal-deployment.modal.run
MARKER_MODAL_TIMEOUT_SECS=600
```

!!! note "Modal Configuration Validation"
    When `MARKER_RUN_MODE=modal`, the `MARKER_MODAL_BASE_URL` must be set. The configuration will fail validation if it's missing.

### Document Preprocessing

Control document preprocessing behavior:

```bash
PREPROCESSING_ENABLED=true
PREPROCESSING_ENABLE_ANALYSIS=true
PREPROCESSING_ROTATE_PAGES=true
PREPROCESSING_ROTATE_PAGES_THRESHOLD=2.0
PREPROCESSING_CLEAN=false
PREPROCESSING_QUIET=false
```

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `PREPROCESSING_ENABLED` | bool | true | Enable/disable preprocessing pipeline |
| `PREPROCESSING_ENABLE_ANALYSIS` | bool | true | Enable document layout analysis |
| `PREPROCESSING_ROTATE_PAGES` | bool | true | Auto-rotate pages based on text orientation |
| `PREPROCESSING_ROTATE_PAGES_THRESHOLD` | float | 2.0 | Confidence threshold for rotation |
| `PREPROCESSING_CLEAN` | bool | false | Clean up temporary files after processing |
| `PREPROCESSING_QUIET` | bool | false | Suppress preprocessing log output |

### Search Engine Configuration

Configure Elasticsearch or OpenSearch for full-text search:

```bash
EXTRALIT_SEARCH_ENGINE=elasticsearch
EXTRALIT_ELASTICSEARCH=http://localhost:9200
```

### Chat & Message Validation

Configure validation limits for chat messages:

```bash
EXTRALIT_MIN_MESSAGE_LENGTH=1
EXTRALIT_MAX_MESSAGE_LENGTH=20000
EXTRALIT_MIN_ROLE_LENGTH=1
EXTRALIT_MAX_ROLE_LENGTH=20
```

## Using Settings in Code

### Importing Settings

```python
from extralit_server.config import settings

# Access configuration values
db_url = settings.EXTRALIT_DATABASE_URL
redis_url = settings.EXTRALIT_REDIS_URL
```

### Accessing Secret Values

For fields defined as `SecretStr`, use `.get_secret_value()` to access the underlying string:

```python
from extralit_server.config import settings

# ❌ Wrong - this returns a SecretStr object
api_key = settings.EXTRALIT_API_KEY

# ✅ Correct - this returns the actual string
api_key = settings.EXTRALIT_API_KEY.get_secret_value()
```

### Debugging Configuration

To see all current settings (with secrets masked):

```python
from extralit_server.config import settings

# Export settings with secrets masked
config_dict = settings.mask_secrets()
print(config_dict)
```

## Environment Variable Naming

Most Extralit settings use the `EXTRALIT_` prefix:

- ✅ `EXTRALIT_DATABASE_URL`
- ✅ `EXTRALIT_REDIS_URL`
- ✅ `EXTRALIT_AUTH_SECRET_KEY`

Some third-party integrations use their own naming:

- `MARKER_RUN_MODE` - Marker-specific
- `MINIO_ACCESS_KEY` - MinIO-specific
- `WCS_HTTP_URL` - Weaviate-specific
- `HF_HUB_DISABLE_TELEMETRY` - HuggingFace-specific

## Validation and Error Handling

The configuration system validates settings at startup. If validation fails, you'll see a clear error message:

```
ValidationError: 1 validation error for Settings
MARKER_MODAL_BASE_URL
  MARKER_MODAL_BASE_URL must be set when MARKER_RUN_MODE is 'modal'.
  Please provide the URL of your Modal deployment endpoint.
```

### Common Validation Errors

#### Missing Required Fields

**Error**: `MARKER_MODAL_BASE_URL must be set when MARKER_RUN_MODE is 'modal'`

**Solution**: Set the required environment variable:
```bash
export MARKER_MODAL_BASE_URL=https://your-modal-deployment.modal.run
```

#### Incomplete S3 Configuration

**Error**: `Incomplete S3 configuration. Missing: EXTRALIT_S3_ACCESS_KEY, EXTRALIT_S3_SECRET_KEY`

**Solution**: Provide all required S3 fields or remove all S3 configuration to use local storage.

## Best Practices

### Development

1. **Use `.env` file**: Keep configuration in `.env` for easy local development
2. **Use SQLite**: Simplest database for local development
3. **Enable debug logging**: Set appropriate log levels for troubleshooting

### Production

1. **Use environment variables**: Set configuration via environment variables (not `.env` file)
2. **Use PostgreSQL**: More robust and performant than SQLite
3. **Set strong secrets**: Generate cryptographically secure secret keys
4. **Enable HTTPS**: Use `EXTRALIT_S3_SECURE=true` for S3 connections
5. **Use Redis**: Required for background jobs and caching
6. **Monitor configuration**: Regularly audit your configuration settings

### Security

1. **Never commit `.env`**: Add `.env` to `.gitignore`
2. **Rotate secrets regularly**: Change secret keys periodically
3. **Use secret management**: Consider using Vault, AWS Secrets Manager, etc.
4. **Limit access**: Restrict who can view/modify production configuration
5. **Audit logs**: Monitor who accesses configuration

## Migration from Old Configuration

If you're upgrading from an older version of Extralit that used direct `os.getenv()` calls:

### Before (Old Pattern)

```python
import os
db_url = os.getenv("EXTRALIT_DATABASE_URL")
```

### After (New Pattern)

```python
from extralit_server.config import settings
db_url = settings.EXTRALIT_DATABASE_URL
```

### Benefits of New Pattern

- ✅ Type safety with automatic validation
- ✅ Clear error messages for missing configuration
- ✅ IDE autocomplete and type hints
- ✅ Documentation available inline
- ✅ Protection against typos

## Troubleshooting

### Configuration Not Loading

**Problem**: Settings don't seem to be loading from `.env` file

**Solutions**:
1. Check that `.env` is in the correct directory (same as `config.py`)
2. Verify `.env` file format (no quotes around values unless needed)
3. Check for typos in variable names
4. Ensure `.env` has proper line endings (Unix LF, not Windows CRLF)

### Import Errors

**Problem**: `ImportError: cannot import name 'settings' from 'extralit_server.config'`

**Solutions**:
1. Ensure you're using the latest version of Extralit Server
2. Check that `config.py` exists in `extralit_server/` directory
3. Verify Python path is set correctly

### Validation Errors at Startup

**Problem**: Server fails to start with validation errors

**Solutions**:
1. Read the error message carefully - it tells you exactly what's wrong
2. Check that all required fields are set
3. Verify field types (e.g., URLs should start with `http://` or `https://`)
4. Ensure boolean values are `true`/`false`, not `yes`/`no`

## Further Reading

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Environment Variables Best Practices](https://12factor.net/config)
- [Extralit Deployment Guide](../admin_guide/deployment.md)
