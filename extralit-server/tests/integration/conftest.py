"""Fixtures for the tests remaining in this tree.

This file used to wire the isolated `/api/v2` suite. That suite is gone; what remains
is `test_rq_groups_workflow.py` (a v1 jobs test) and `index/` (the LanceDB engine,
kept for ENG-36 and fixture-free). New tests belong under `tests/unit/` — see the
plan's "The server test tree is named backwards" note.
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.database import get_async_db
from extralit_server.models import User
from tests.database import TestSession
from tests.factories import OwnerFactory


@pytest_asyncio.fixture
async def owner() -> User:
    return await OwnerFactory.create(first_name="Owner", username="owner", api_key="owner.apikey")


@pytest.fixture
def owner_auth_header(owner: User) -> dict[str, str]:
    return {API_KEY_HEADER_NAME: owner.api_key}


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    from extralit_server import app
    from extralit_server.api.routes import api_v1

    async def override_get_async_db():
        yield TestSession()

    api_v1.dependency_overrides[get_async_db] = override_get_async_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client

    # Pop only what this fixture registered. `tests/unit/conftest.py`'s async_client writes
    # into the same `api_v1.dependency_overrides` dict, so a blanket clear() here would wipe
    # its keys — benign only while tests/integration happens to collect first, and broken
    # under -p randomly or an explicit `pytest tests/unit tests/integration`.
    api_v1.dependency_overrides.pop(get_async_db, None)
