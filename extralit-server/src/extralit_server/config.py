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

from typing import Optional

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # From extralit/.env.test
    EXTRALIT_API_URL: Optional[HttpUrl] = None
    EXTRALIT_API_KEY: Optional[SecretStr] = None

    # From extralit-server/.env.dev and extralit-server/.env.test
    OBJC_DISABLE_INITIALIZE_FORK_SAFETY: Optional[str] = None
    ALEMBIC_CONFIG: Optional[str] = None
    EXTRALIT_AUTH_SECRET_KEY: Optional[SecretStr] = None
    EXTRALIT_DATABASE_URL: str = "sqlite+aiosqlite:///./extralit-dev.db?check_same_thread=False"
    HF_HUB_DISABLE_TELEMETRY: bool = True
    EXTRALIT_S3_ENDPOINT: Optional[HttpUrl] = None
    EXTRALIT_S3_ACCESS_KEY: Optional[str] = None
    EXTRALIT_S3_SECRET_KEY: Optional[SecretStr] = None
    EXTRALIT_S3_REGION: Optional[str] = None
    EXTRALIT_S3_SECURE: bool = False
    EXTRALIT_EXTRALIT_URL: Optional[HttpUrl] = None
    EXTRALIT_SEARCH_ENGINE: Optional[str] = None
    EXTRALIT_ELASTICSEARCH: Optional[HttpUrl] = None
    EXTRALIT_REDIS_URL: str = "redis://localhost:6379/0"
    PREPROCESSING_ENABLED: bool = True
    PREPROCESSING_ENABLE_ANALYSIS: bool = True
    PREPROCESSING_ROTATE_PAGES: bool = True
    PREPROCESSING_ROTATE_PAGES_THRESHOLD: float = 2.0
    PREPROCESSING_CLEAN: bool = False
    PREPROCESSING_QUIET: bool = False

    # From .devcontainer/docker-compose/.env.dev
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[SecretStr] = None
    WCS_HTTP_URL: Optional[str] = None
    WCS_GRPC_URL: Optional[str] = None
    WCS_API_KEY: Optional[SecretStr] = None
    WCS_USERNAME: Optional[str] = None
    WCS_PASSWORD: Optional[SecretStr] = None


settings = Settings()
