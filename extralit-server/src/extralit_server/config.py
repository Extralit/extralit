# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Centralized configuration management for Extralit Server.

This module provides a Pydantic-based settings class that loads configuration
from environment variables and .env files. All environment variable access
should go through the `settings` object to ensure type safety and validation.

Usage:
    from extralit_server.config import settings

    # Access settings
    db_url = settings.EXTRALIT_DATABASE_URL
    api_key = settings.EXTRALIT_API_KEY.get_secret_value()  # For SecretStr fields
"""

from typing import Optional

from pydantic import Field, HttpUrl, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Settings are loaded from:
    1. Environment variables
    2. .env file (if present)
    3. Default values defined in field declarations

    Most settings use the EXTRALIT_ prefix, but some third-party integrations
    (Marker, MinIO, etc.) use their own naming conventions.

    For sensitive values (API keys, secrets), use the .get_secret_value() method
    to access the underlying string value.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Client API Configuration
    EXTRALIT_API_URL: Optional[HttpUrl] = Field(
        default=None, description="URL of the Extralit API server for client connections"
    )
    EXTRALIT_API_KEY: Optional[SecretStr] = Field(
        default=None, description="API key for authenticating with Extralit server"
    )

    # Server Configuration
    OBJC_DISABLE_INITIALIZE_FORK_SAFETY: Optional[str] = Field(
        default=None, description="macOS-specific setting to disable Objective-C fork safety warnings"
    )
    ALEMBIC_CONFIG: Optional[str] = Field(default=None, description="Path to Alembic configuration file")
    EXTRALIT_AUTH_SECRET_KEY: Optional[SecretStr] = Field(
        default=None, description="Secret key for JWT token signing and authentication"
    )
    EXTRALIT_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./extralit-dev.db?check_same_thread=False",
        description="Database connection URL (supports SQLite and PostgreSQL)",
    )
    HF_HUB_DISABLE_TELEMETRY: bool = Field(default=True, description="Disable HuggingFace Hub telemetry collection")
    # S3 Storage Configuration
    EXTRALIT_S3_ENDPOINT: Optional[HttpUrl] = Field(
        default=None, description="S3-compatible storage endpoint URL (e.g., MinIO, AWS S3)"
    )
    EXTRALIT_S3_ACCESS_KEY: Optional[str] = Field(default=None, description="S3 access key ID")
    EXTRALIT_S3_SECRET_KEY: Optional[SecretStr] = Field(default=None, description="S3 secret access key")
    EXTRALIT_S3_REGION: Optional[str] = Field(default=None, description="S3 bucket region")
    EXTRALIT_S3_SECURE: bool = Field(default=False, description="Use HTTPS for S3 connections")

    # Search and Cache Configuration
    EXTRALIT_EXTRALIT_URL: Optional[HttpUrl] = Field(default=None, description="URL for Extralit LLM serving endpoint")
    EXTRALIT_SEARCH_ENGINE: Optional[str] = Field(
        default=None, description="Search engine backend (elasticsearch or opensearch)"
    )
    EXTRALIT_ELASTICSEARCH: Optional[HttpUrl] = Field(default=None, description="Elasticsearch/OpenSearch endpoint URL")
    EXTRALIT_REDIS_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL for caching and job queues"
    )
    # Document Preprocessing Configuration
    PREPROCESSING_ENABLED: bool = Field(default=True, description="Enable document preprocessing pipeline")
    PREPROCESSING_ENABLE_ANALYSIS: bool = Field(default=True, description="Enable document layout analysis")
    PREPROCESSING_ROTATE_PAGES: bool = Field(default=True, description="Auto-rotate pages based on text orientation")
    PREPROCESSING_ROTATE_PAGES_THRESHOLD: float = Field(
        default=2.0, description="Confidence threshold for page rotation detection"
    )
    PREPROCESSING_CLEAN: bool = Field(default=False, description="Clean up temporary files after preprocessing")
    PREPROCESSING_QUIET: bool = Field(default=False, description="Suppress preprocessing log output")

    # External Service Configuration (MinIO, Weaviate)
    MINIO_ACCESS_KEY: Optional[str] = Field(default=None, description="MinIO access key for object storage")
    MINIO_SECRET_KEY: Optional[SecretStr] = Field(default=None, description="MinIO secret key")
    WCS_HTTP_URL: Optional[str] = Field(default=None, description="Weaviate Cloud Services HTTP endpoint")
    WCS_GRPC_URL: Optional[str] = Field(default=None, description="Weaviate Cloud Services gRPC endpoint")
    WCS_API_KEY: Optional[SecretStr] = Field(default=None, description="Weaviate Cloud Services API key")
    WCS_USERNAME: Optional[str] = Field(default=None, description="Weaviate Cloud Services username")
    WCS_PASSWORD: Optional[SecretStr] = Field(default=None, description="Weaviate Cloud Services password")

    # Marker PDF Processing Configuration
    MARKER_RUN_MODE: str = Field(
        default="local", description="Marker execution mode: 'local' for in-process or 'modal' for remote API"
    )
    MARKER_MODAL_BASE_URL: Optional[str] = Field(
        default=None, description="Base URL for Modal-hosted Marker service (required when MARKER_RUN_MODE=modal)"
    )
    MARKER_MODAL_TIMEOUT_SECS: int = Field(default=600, description="Timeout in seconds for Modal Marker API calls")

    # Chat and Message Validation
    EXTRALIT_MIN_MESSAGE_LENGTH: int = Field(default=1, description="Minimum chat message length")
    EXTRALIT_MAX_MESSAGE_LENGTH: int = Field(default=20000, description="Maximum chat message length")
    EXTRALIT_MIN_ROLE_LENGTH: int = Field(default=1, description="Minimum chat role name length")
    EXTRALIT_MAX_ROLE_LENGTH: int = Field(default=20, description="Maximum chat role name length")

    # Authentication Configuration
    EXTRALIT_LOCAL_AUTH_USERS_DB_FILE: str = Field(
        default=".users.yml", description="Path to local users database file for authentication"
    )

    @field_validator("MARKER_MODAL_BASE_URL")
    @classmethod
    def validate_marker_modal_url(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that MARKER_MODAL_BASE_URL is set when using Modal mode."""
        if info.data.get("MARKER_RUN_MODE", "").lower() == "modal" and not v:
            raise ValueError(
                "MARKER_MODAL_BASE_URL must be set when MARKER_RUN_MODE is 'modal'. "
                "Please provide the URL of your Modal deployment endpoint."
            )
        return v

    @model_validator(mode="after")
    def validate_s3_config(self) -> "Settings":
        """Validate that S3 configuration is complete when any S3 field is provided."""
        s3_fields = {
            "EXTRALIT_S3_ENDPOINT": self.EXTRALIT_S3_ENDPOINT,
            "EXTRALIT_S3_ACCESS_KEY": self.EXTRALIT_S3_ACCESS_KEY,
            "EXTRALIT_S3_SECRET_KEY": self.EXTRALIT_S3_SECRET_KEY,
        }
        provided_fields = {k: v for k, v in s3_fields.items() if v is not None}

        # If any S3 field is provided, all required fields must be provided
        if provided_fields and len(provided_fields) < 3:
            missing = [k for k, v in s3_fields.items() if v is None]
            raise ValueError(
                f"Incomplete S3 configuration. When using S3 storage, all required fields must be set. "
                f"Missing: {', '.join(missing)}"
            )
        return self

    def mask_secrets(self) -> dict:
        """Export settings with sensitive values masked for logging/debugging.

        Returns:
            dict: Settings dictionary with SecretStr fields masked as '***'
        """
        data = self.model_dump()
        for key, value in data.items():
            if isinstance(getattr(self, key), SecretStr) and value:
                data[key] = "***MASKED***"
        return data


settings = Settings()
