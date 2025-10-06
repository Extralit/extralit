# Configuration System (Developer Guide)

This guide explains the Pydantic-based configuration system for Extralit Server developers.

## Architecture

The configuration system uses Pydantic Settings to provide type-safe, validated configuration management.

### Key Components

```
extralit-server/
├── src/extralit_server/
│   └── config.py           # Central configuration module
├── .env.example            # Configuration template
└── .env                    # Local configuration (gitignored)
```

## The Settings Class

Located in `extralit_server/config.py`, the `Settings` class is a Pydantic model that defines all configuration options:

```python
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    EXTRALIT_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./extralit-dev.db",
        description="Database connection URL"
    )

    EXTRALIT_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="API key for authentication"
    )

settings = Settings()  # Global singleton instance
```

## Adding New Configuration Options

### 1. Define the Field

Add the field to the `Settings` class in `config.py`:

```python
class Settings(BaseSettings):
    # ... existing fields ...

    MY_NEW_FEATURE_ENABLED: bool = Field(
        default=False,
        description="Enable my awesome new feature"
    )

    MY_NEW_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description="API key for my new service"
    )
```

### 2. Use Field() for Documentation

Always use `Field()` with a `description` parameter:

```python
# ❌ Bad - no documentation
MY_SETTING: str = "default"

# ✅ Good - includes description
MY_SETTING: str = Field(
    default="default",
    description="What this setting does"
)
```

### 3. Choose the Right Type

Use appropriate types for validation:

```python
# Strings
MY_STRING: str = Field(default="value", description="...")

# URLs (validated)
MY_URL: HttpUrl = Field(default=None, description="...")

# Secrets (protected from logging)
MY_SECRET: SecretStr = Field(default=None, description="...")

# Integers
MY_NUMBER: int = Field(default=100, description="...")

# Floats
MY_THRESHOLD: float = Field(default=0.5, description="...")

# Booleans
MY_FLAG: bool = Field(default=True, description="...")

# Optional values
MY_OPTIONAL: Optional[str] = Field(default=None, description="...")
```

### 4. Add Validation (if needed)

Use Pydantic validators for complex validation logic:

```python
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    MY_MODE: str = Field(default="auto", description="...")
    MY_URL: Optional[str] = Field(default=None, description="...")

    @field_validator("MY_URL")
    @classmethod
    def validate_my_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate MY_URL is set when MY_MODE requires it."""
        if info.data.get("MY_MODE") == "remote" and not v:
            raise ValueError(
                "MY_URL must be set when MY_MODE is 'remote'"
            )
        return v

    @model_validator(mode="after")
    def validate_complete_config(self) -> "Settings":
        """Cross-field validation."""
        # Check relationships between multiple fields
        return self
```

### 5. Update Documentation

Add the new setting to:

1. `.env.example` - with commented example
2. `docs/admin_guide/configuration.md` - with full documentation

## Using Settings in Your Code

### Basic Usage

```python
from extralit_server.config import settings

def my_function():
    db_url = settings.EXTRALIT_DATABASE_URL
    timeout = settings.MARKER_MODAL_TIMEOUT_SECS
```

### Accessing Secrets

For `SecretStr` fields, use `.get_secret_value()`:

```python
from extralit_server.config import settings

def authenticate():
    # ❌ Wrong - returns SecretStr object
    api_key = settings.EXTRALIT_API_KEY

    # ✅ Correct - returns the actual string
    if settings.EXTRALIT_API_KEY:
        api_key = settings.EXTRALIT_API_KEY.get_secret_value()
```

### Conditional Logic

```python
from extralit_server.config import settings

if settings.MARKER_RUN_MODE == "modal":
    # Use Modal API
    url = settings.MARKER_MODAL_BASE_URL
else:
    # Use local processing
    pass
```

## Type Safety Benefits

The Pydantic settings system provides strong type safety:

### IDE Autocomplete

Modern IDEs will autocomplete setting names and show types:

```python
from extralit_server.config import settings

settings.  # IDE shows all available settings with types
```

### Type Checking

Tools like `mypy` can catch errors at development time:

```python
# mypy will catch this error
timeout: int = settings.EXTRALIT_DATABASE_URL  # Type mismatch!
```

### Runtime Validation

Invalid values are caught immediately:

```bash
# This will fail at startup
export EXTRALIT_REDIS_URL="not-a-valid-url"
```

## Testing with Settings

### Override Settings in Tests

Use Pydantic's test utilities or monkeypatch:

```python
import pytest
from extralit_server.config import Settings

def test_with_custom_settings(monkeypatch):
    # Method 1: Patch environment variables
    monkeypatch.setenv("MARKER_RUN_MODE", "modal")
    monkeypatch.setenv("MARKER_MODAL_BASE_URL", "https://test.example.com")

    # Reload settings
    from extralit_server import config
    config.settings = Settings()

    # Now test with the new settings
    assert config.settings.MARKER_RUN_MODE == "modal"
```

```python
def test_with_settings_override():
    # Method 2: Create a test settings instance
    test_settings = Settings(
        MARKER_RUN_MODE="local",
        EXTRALIT_DATABASE_URL="sqlite:///:memory:"
    )

    # Use test_settings in your test
    assert test_settings.MARKER_RUN_MODE == "local"
```

### Testing Validation

Test that validation works correctly:

```python
import pytest
from pydantic import ValidationError
from extralit_server.config import Settings

def test_marker_modal_validation():
    # Should raise error when modal mode without URL
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            MARKER_RUN_MODE="modal",
            MARKER_MODAL_BASE_URL=None
        )

    assert "MARKER_MODAL_BASE_URL must be set" in str(exc_info.value)
```

## Migration Patterns

### Replacing os.getenv()

When you find code using `os.getenv()`, refactor it to use settings:

```python
# Before
import os
timeout = int(os.getenv("TIMEOUT", "60"))

# After
from extralit_server.config import settings
timeout = settings.MY_TIMEOUT  # Already typed as int
```

### Replacing os.environ

```python
# Before
import os
api_key = os.environ["API_KEY"]

# After
from extralit_server.config import settings
api_key = settings.MY_API_KEY.get_secret_value()
```

### Handling Defaults

```python
# Before
value = os.getenv("SETTING", "default")

# After
# Define default in Settings class
MY_SETTING: str = Field(default="default", description="...")

# Then use directly
value = settings.MY_SETTING
```

## Common Patterns

### Feature Flags

```python
class Settings(BaseSettings):
    FEATURE_NEW_UI_ENABLED: bool = Field(
        default=False,
        description="Enable new UI features"
    )

# Usage
from extralit_server.config import settings

if settings.FEATURE_NEW_UI_ENABLED:
    return render_new_ui()
else:
    return render_old_ui()
```

### Environment-Specific Defaults

```python
import os
from pydantic import Field

class Settings(BaseSettings):
    DEBUG: bool = Field(
        default=os.getenv("ENV") == "development",
        description="Enable debug mode"
    )
```

### Computed Properties

```python
class Settings(BaseSettings):
    REDIS_HOST: str = Field(default="localhost", description="...")
    REDIS_PORT: int = Field(default=6379, description="...")

    @property
    def redis_url(self) -> str:
        """Computed Redis URL from host and port."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"
```

## Security Best Practices

### Always Use SecretStr for Secrets

```python
# ❌ Bad - secret visible in logs
MY_SECRET: str = Field(default=None, description="...")

# ✅ Good - secret protected
MY_SECRET: SecretStr = Field(default=None, description="...")
```

### Implement mask_secrets()

The `Settings` class includes a `mask_secrets()` method for safe logging:

```python
from extralit_server.config import settings

# Safe to log - secrets are masked
config_dict = settings.mask_secrets()
logger.info(f"Configuration: {config_dict}")
```

### Validate Secret Strength

```python
@field_validator("EXTRALIT_AUTH_SECRET_KEY")
@classmethod
def validate_secret_key_strength(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
    if v:
        secret = v.get_secret_value()
        if len(secret) < 32:
            raise ValueError("Secret key must be at least 32 characters")
    return v
```

## Performance Considerations

### Settings are Loaded Once

The `settings` object is created once at import time:

```python
# config.py
settings = Settings()  # Loaded once

# When you import
from extralit_server.config import settings  # Reuses same instance
```

### Avoid Repeated Access in Loops

```python
# ❌ Less efficient
for item in large_list:
    if settings.MY_FLAG:  # Settings access in loop
        process(item)

# ✅ More efficient
my_flag = settings.MY_FLAG  # Access once
for item in large_list:
    if my_flag:
        process(item)
```

## Troubleshooting

### Circular Import Issues

If you get circular import errors:

```python
# ❌ Can cause circular imports
from extralit_server.config import settings  # At module level

def my_function():
    pass

# ✅ Import inside function if needed
def my_function():
    from extralit_server.config import settings
    return settings.MY_VALUE
```

### Type Checker Complaints

If mypy complains about optional values:

```python
# ❌ mypy error: Optional[str] not compatible with str
url: str = settings.MY_OPTIONAL_URL

# ✅ Handle the optional case
url = settings.MY_OPTIONAL_URL or "default"

# ✅ Or use type narrowing
if settings.MY_OPTIONAL_URL:
    url: str = settings.MY_OPTIONAL_URL  # Now mypy knows it's not None
```

## References

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Pydantic Validation](https://docs.pydantic.dev/latest/concepts/validators/)
- [Twelve-Factor App Config](https://12factor.net/config)
