import json
import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Schemas

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
WS = str(uuid.uuid4())
SCHEMA_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _schema(name="trials"):
    return {
        "id": SCHEMA_ID,
        "name": name,
        "status": "draft",
        "current_version_id": None,
        "settings": {},
        "workspace_id": WS,
        "inserted_at": NOW,
        "updated_at": NOW,
    }


def _version(version=1):
    return {
        "id": str(uuid.uuid4()),
        "schema_id": SCHEMA_ID,
        "version": version,
        "object_key": f"schemas/{SCHEMA_ID}/v{version}.json",
        "object_version_id": None,
        "etag": "e",
        "checksum": "c",
        "parent_version_id": None,
        "columns_cache": [{"name": "size"}],
        "review_widgets": {},
        "inserted_at": NOW,
    }


@pytest.fixture
def schemas():
    transport = AsyncTransport(API, api_key="k")
    yield Schemas(transport)
    # Note: aclose() is handled by pytest-asyncio context manager


async def test_create_and_get(httpx_mock, schemas):
    httpx_mock.add_response(method="POST", url=f"{API}/api/v2/schemas", status_code=201, json=_schema())
    created = await schemas.create(WS, "trials")
    assert created.name == "trials"
    body = httpx_mock.get_requests()[0].read()
    assert b'"workspace_id"' in body and b'"trials"' in body


async def test_get_by_name_found_and_missing(httpx_mock, schemas):
    listing = {"items": [_schema("other") | {"id": str(uuid.uuid4())}, _schema("trials")]}
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id={WS}", json=listing)
    found = await schemas.get_by_name(WS, "trials")
    assert str(found.id) == SCHEMA_ID
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id={WS}", json={"items": []})
    with pytest.raises(NotFoundError):
        await schemas.get_by_name(WS, "trials")


async def test_publish_accepts_pandera_object_or_string(httpx_mock, schemas):
    httpx_mock.add_response(
        method="POST",
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions",
        status_code=201,
        json=_version(),
    )

    class FakePandera:  # duck-type: anything with .to_json()
        def to_json(self):
            return '{"columns": {"size": {}}}'

    version = await schemas.publish(SCHEMA_ID, FakePandera(), review_widgets={"size": {"widget": "text"}})
    assert version.version == 1
    sent = json.loads(httpx_mock.get_requests()[0].read())
    assert set(sent) == {
        "body",
        "review_widgets",
    }  # review_widgets ride out-of-band, not merged into body
    assert sent["review_widgets"] == {"size": {"widget": "text"}}
    assert '"columns"' in sent["body"]  # body is the pandera JSON string, kept as a string value


async def test_get_version_cached(httpx_mock, schemas):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions/1", json=_version())
    v1 = await schemas.get_version(SCHEMA_ID, 1)
    v1_again = await schemas.get_version(SCHEMA_ID, 1)  # served from cache: no second request
    assert v1_again is v1
    assert len(httpx_mock.get_requests()) == 1


async def test_versions_and_columns(httpx_mock, schemas):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions",
        json=[_version(1), _version(2)],
    )
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/columns", json=[{"name": "size"}])
    assert [v.version for v in await schemas.versions(SCHEMA_ID)] == [1, 2]
    assert await schemas.columns(SCHEMA_ID) == [{"name": "size"}]
