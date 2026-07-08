import pytest

from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import SchemaFactory, SchemaVersionFactory, V2QuestionFactory, V2RecordFactory

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
