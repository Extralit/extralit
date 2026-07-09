from unittest.mock import AsyncMock, patch

import pytest

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import (
    AnnotatorFactory,
    SchemaFactory,
    SchemaVersionFactory,
    V2QuestionFactory,
    V2RecordFactory,
    WorkspaceUserFactory,
)

pytestmark = pytest.mark.asyncio

COLUMNS_CACHE = [{"name": "disease", "dtype": "str", "nullable": True, "review": None}]


async def _published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(schema=schema, columns_cache=COLUMNS_CACHE)
    schema.current_version_id = version.id
    await db.commit()
    return schema


async def test_upsert_suggestion_happy_and_idempotent(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    question = await V2QuestionFactory.create(
        schema=schema, type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    record = await V2RecordFactory.create(version__schema=schema)

    resp = await async_client.put(
        f"/api/v2/records/{record.id}/suggestions",
        headers=owner_auth_header,
        json={"question_id": str(question.id), "value": "a"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["value"] == "a"
    assert body["record_id"] == str(record.id)
    assert body["question_id"] == str(question.id)
    suggestion_id = body["id"]

    # Re-PUT with the same (record, question) pair updates the same row idempotently.
    resp = await async_client.put(
        f"/api/v2/records/{record.id}/suggestions",
        headers=owner_auth_header,
        json={"question_id": str(question.id), "value": "b"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == suggestion_id
    assert body["value"] == "b"


async def test_upsert_suggestion_rejects_question_from_other_schema(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    record = await V2RecordFactory.create(version__schema=schema)

    other_schema = await _published_schema(db)
    other_question = await V2QuestionFactory.create(
        schema=other_schema, type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )

    resp = await async_client.put(
        f"/api/v2/records/{record.id}/suggestions",
        headers=owner_auth_header,
        json={"question_id": str(other_question.id), "value": "a"},
    )
    assert resp.status_code == 422, resp.text


async def test_list_suggestions_returns_upserted(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    question = await V2QuestionFactory.create(
        schema=schema, type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    record = await V2RecordFactory.create(version__schema=schema)

    put_resp = await async_client.put(
        f"/api/v2/records/{record.id}/suggestions",
        headers=owner_auth_header,
        json={"question_id": str(question.id), "value": "a"},
    )
    assert put_resp.status_code == 200, put_resp.text

    list_resp = await async_client.get(f"/api/v2/records/{record.id}/suggestions", headers=owner_auth_header)
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["question_id"] == str(question.id)
    assert items[0]["value"] == "a"


async def test_non_member_annotator_cannot_read_suggestions(async_client, annotator_auth_header, db):
    # The annotator behind annotator_auth_header is NOT a member of this schema's workspace.
    schema = await _published_schema(db)
    record = await V2RecordFactory.create(version__schema=schema)

    resp = await async_client.get(f"/api/v2/records/{record.id}/suggestions", headers=annotator_auth_header)
    assert resp.status_code == 403, resp.text


async def test_member_non_admin_annotator_cannot_upsert_suggestion(async_client, annotator, annotator_auth_header, db):
    # V2SuggestionPolicy.write requires owner or admin+member; a plain (non-admin) member
    # must still be forbidden from writing suggestions even though they can read them.
    schema = await _published_schema(db)
    question = await V2QuestionFactory.create(
        schema=schema, type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    record = await V2RecordFactory.create(version__schema=schema)
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=annotator.id)

    resp = await async_client.put(
        f"/api/v2/records/{record.id}/suggestions",
        headers=annotator_auth_header,
        json={"question_id": str(question.id), "value": "a"},
    )
    assert resp.status_code == 403, resp.text


async def test_annotator_upserts_own_response(async_client, annotator, annotator_auth_header, db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}, required=True
    )
    record = await V2RecordFactory.create(version__schema=schema)
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=annotator.id)

    resp = await async_client.put(
        f"/api/v2/records/{record.id}/responses",
        headers=annotator_auth_header,
        json={"status": "submitted", "values": {"dx": {"value": "flu"}}},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["values"] == {"dx": {"value": "flu"}}
    assert body["status"] == "submitted"
    assert body["user_id"] == str(annotator.id)
    assert body["record_id"] == str(record.id)

    get_resp = await async_client.get(f"/api/v2/records/{record.id}/responses", headers=annotator_auth_header)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["values"] == {"dx": {"value": "flu"}}


async def test_second_annotator_gets_only_their_own_response(async_client, annotator, annotator_auth_header, db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}, required=True
    )
    record = await V2RecordFactory.create(version__schema=schema)
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=annotator.id)

    put_resp = await async_client.put(
        f"/api/v2/records/{record.id}/responses",
        headers=annotator_auth_header,
        json={"status": "submitted", "values": {"dx": {"value": "flu"}}},
    )
    assert put_resp.status_code == 200, put_resp.text

    second_annotator = await AnnotatorFactory.create(username="annotator-2", api_key="annotator-2.apikey")
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=second_annotator.id)
    second_auth_header = {API_KEY_HEADER_NAME: second_annotator.api_key}

    get_resp = await async_client.get(f"/api/v2/records/{record.id}/responses", headers=second_auth_header)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json() is None  # the second annotator has not submitted their own response yet


async def test_non_member_annotator_cannot_read_or_upsert_response(async_client, annotator_auth_header, db):
    # The annotator behind annotator_auth_header is NOT a member of this schema's workspace.
    # V2ResponsePolicy.read/upsert_own both require owner-or-member, so authorization is
    # denied before question/value validation runs regardless of the request payload.
    schema = await _published_schema(db)
    record = await V2RecordFactory.create(version__schema=schema)

    get_resp = await async_client.get(f"/api/v2/records/{record.id}/responses", headers=annotator_auth_header)
    assert get_resp.status_code == 403, get_resp.text

    put_resp = await async_client.put(
        f"/api/v2/records/{record.id}/responses",
        headers=annotator_auth_header,
        json={"status": "submitted", "values": {"dx": {"value": "flu"}}},
    )
    assert put_resp.status_code == 403, put_resp.text


async def test_response_upsert_does_not_sync_lance(async_client, annotator, annotator_auth_header, db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}, required=True
    )
    record = await V2RecordFactory.create(version__schema=schema)
    await WorkspaceUserFactory.create(workspace_id=schema.workspace_id, user_id=annotator.id)

    with patch("extralit_server.contexts.v2.index_sync.sync_upserted_records", new=AsyncMock()) as synced:
        resp = await async_client.put(
            f"/api/v2/records/{record.id}/responses",
            headers=annotator_auth_header,
            json={"status": "submitted", "values": {"dx": {"value": "flu"}}},
        )
    assert resp.status_code == 200, resp.text
    synced.assert_not_called()  # annotation never touches the index engine (spec §17.5)
