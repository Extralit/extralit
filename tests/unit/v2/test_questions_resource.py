import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Questions

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
Q_SIZE = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _question(qid, name):
    return {
        "id": qid,
        "schema_id": SCHEMA_ID,
        "name": name,
        "title": name.title(),
        "description": None,
        "type": "text",
        "columns": [name],
        "settings": {},
        "required": False,
        "inserted_at": NOW,
        "updated_at": NOW,
    }


@pytest.fixture
def questions():
    transport = AsyncTransport(API, api_key="k")
    return Questions(transport)


async def test_list_and_id_for_uses_one_fetch(httpx_mock, questions):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={"items": [_question(Q_SIZE, "size")]},
    )
    assert [q.name for q in await questions.list(SCHEMA_ID)] == ["size"]
    assert str(await questions.id_for(SCHEMA_ID, "size")) == Q_SIZE  # served from cache
    assert len(httpx_mock.get_requests()) == 1


async def test_id_for_refetches_once_then_raises(httpx_mock, questions):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={"items": [_question(Q_SIZE, "size")]},
    )
    await questions.list(SCHEMA_ID)
    q_new = str(uuid.uuid4())
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={"items": [_question(Q_SIZE, "size"), _question(q_new, "dosage")]},
    )
    assert (
        str(await questions.id_for(SCHEMA_ID, "dosage")) == q_new
    )  # miss -> refetch -> hit
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions", json={"items": []}
    )
    with pytest.raises(NotFoundError):
        await questions.id_for(SCHEMA_ID, "ghost")
