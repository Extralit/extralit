import uuid
from datetime import datetime, timezone

from extralit.v2.models import (
    Record,
    Response,
    SchemaVersion,
    SearchPage,
    unwrap_response_values,
    wrap_response_values,
)


def _version_payload(**overrides):
    payload = {
        "id": str(uuid.uuid4()),
        "schema_id": str(uuid.uuid4()),
        "version": 1,
        "object_key": "schemas/x/v1.json",
        "object_version_id": None,
        "etag": "e",
        "checksum": "c",
        "parent_version_id": None,
        "columns_cache": [{"name": "size", "dtype": "str"}, {"name": "country", "dtype": "str"}],
        "review_widgets": {},
        "inserted_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_schema_version_find_column():
    version = SchemaVersion.model_validate(_version_payload())
    assert version.find_column("size") == {"name": "size", "dtype": "str"}
    assert version.find_column("nope") is None


def test_wrap_unwrap_roundtrip():
    """Server double-wraps response values ({name: {"value": ...}}) on both PUT and GET."""
    values = {"size": "120", "country": ["KE", "UG"]}
    wrapped = wrap_response_values(values)
    assert wrapped == {"size": {"value": "120"}, "country": {"value": ["KE", "UG"]}}
    assert unwrap_response_values(wrapped) == values
    assert unwrap_response_values(None) == {}


def test_response_unwrapped_values():
    response = Response.model_validate(
        {
            "id": str(uuid.uuid4()),
            "record_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "values": {"size": {"value": "135"}},
            "status": "submitted",
            "inserted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    assert response.unwrapped_values == {"size": "135"}


def test_search_page_holds_records():
    record = {
        "id": str(uuid.uuid4()),
        "schema_id": str(uuid.uuid4()),
        "schema_version_id": str(uuid.uuid4()),
        "reference": "10.1000/xyz",
        "external_id": None,
        "fields": {"size": "120"},
        "metadata": None,
        "status": "pending",
        "inserted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    page = SearchPage(items=[Record.model_validate(record)], total=1)
    assert page.items[0].reference == "10.1000/xyz"
    assert page.total == 1
