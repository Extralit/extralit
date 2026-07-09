import pytest

from extralit_server.enums import QuestionType, SchemaStatus
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio

COLUMNS_CACHE = [{"name": "disease", "dtype": "str", "nullable": True, "review": None}]


async def _published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(schema=schema, columns_cache=COLUMNS_CACHE)
    schema.current_version_id = version.id
    await db.commit()
    return schema


async def test_create_question_happy(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["disease"]},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["columns"] == ["disease"]
    assert body["schema_id"] == str(schema.id)
    assert body["name"] == "dx"
    assert body["required"] is False


async def test_create_question_unknown_column_rejected(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["nope"]},
    )
    assert resp.status_code == 422, resp.text


async def test_create_question_span_rejected(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "s", "title": "S", "type": QuestionType.span.value, "columns": ["disease"]},
    )
    assert resp.status_code == 422


async def test_list_questions_returns_created(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    create_resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["disease"]},
    )
    assert create_resp.status_code == 201, create_resp.text
    question_id = create_resp.json()["id"]

    list_resp = await async_client.get(f"/api/v2/schemas/{schema.id}/questions", headers=owner_auth_header)
    assert list_resp.status_code == 200, list_resp.text
    ids = [item["id"] for item in list_resp.json()["items"]]
    assert ids == [question_id]


async def test_get_update_delete_question(async_client, owner_auth_header, db):
    schema = await _published_schema(db)
    create_resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=owner_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["disease"]},
    )
    question_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/v2/questions/{question_id}", headers=owner_auth_header)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == question_id

    put_resp = await async_client.put(
        f"/api/v2/questions/{question_id}",
        headers=owner_auth_header,
        json={"title": "Diagnosis (updated)", "required": True},
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["title"] == "Diagnosis (updated)"
    assert put_resp.json()["required"] is True

    delete_resp = await async_client.delete(f"/api/v2/questions/{question_id}", headers=owner_auth_header)
    assert delete_resp.status_code == 204

    missing_resp = await async_client.get(f"/api/v2/questions/{question_id}", headers=owner_auth_header)
    assert missing_resp.status_code == 404


async def test_non_member_annotator_cannot_create_question(async_client, annotator_auth_header, db):
    # The annotator behind annotator_auth_header is NOT a member of this schema's workspace.
    schema = await _published_schema(db)
    resp = await async_client.post(
        f"/api/v2/schemas/{schema.id}/questions",
        headers=annotator_auth_header,
        json={"name": "dx", "title": "Dx", "type": QuestionType.text.value, "columns": ["disease"]},
    )
    assert resp.status_code == 403, resp.text
