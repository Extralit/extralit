"""Fixtures for the isolated v2 (`/api/v2`) test suite.

These mirror the v1 fixtures in `tests/unit/conftest.py` but deliberately omit the
session-scoped OpenSearch fixture (v2 does not use Elasticsearch/OpenSearch) and wire
the test database + a mocked S3 client onto the separately-mounted `api_v2` sub-app.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import AsyncClient

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts import files as files_ctx
from extralit_server.database import get_async_db
from extralit_server.models import User
from tests.database import TestSession
from tests.factories import AnnotatorFactory, OwnerFactory


@pytest_asyncio.fixture
async def owner() -> User:
    return await OwnerFactory.create(first_name="Owner", username="owner", api_key="owner.apikey")


@pytest_asyncio.fixture
async def annotator() -> User:
    return await AnnotatorFactory.create(first_name="Annotator", username="annotator", api_key="annotator.apikey")


@pytest.fixture
def owner_auth_header(owner: User) -> dict[str, str]:
    return {API_KEY_HEADER_NAME: owner.api_key}


@pytest.fixture
def annotator_auth_header(annotator: User) -> dict[str, str]:
    return {API_KEY_HEADER_NAME: annotator.api_key}


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from extralit_server import app
    from extralit_server.api.v2 import api_v2

    async def override_get_async_db():
        yield TestSession()

    async def override_get_s3_client():
        # publish_version uploads via contexts.files.put_object, which tests monkeypatch; the
        # yielded client is never used for real I/O, so a bare AsyncMock is sufficient.
        yield AsyncMock()

    api_v2.dependency_overrides[get_async_db] = override_get_async_db
    api_v2.dependency_overrides[files_ctx.get_s3_client] = override_get_s3_client

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

    api_v2.dependency_overrides.clear()
