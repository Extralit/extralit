import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from extralit.v2._api._generated import Source
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Record
from extralit.v2.resources import Projections, Questions, Responses, Suggestions

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
RECORD_ID = str(uuid.uuid4())
Q_SIZE = str(uuid.uuid4())
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _suggestion():
    return {
        "id": str(uuid.uuid4()),
        "record_id": RECORD_ID,
        "question_id": Q_SIZE,
        "value": "120",
        "score": 0.9,
        "agent": "claude",
        "type": "model",
        "inserted_at": NOW,
        "updated_at": NOW,
    }


def _record_obj():
    return Record.model_validate(
        {
            "id": RECORD_ID,
            "schema_id": SCHEMA_ID,
            "schema_version_id": str(uuid.uuid4()),
            "reference": "10.1000/xyz",
            "external_id": None,
            "fields": {},
            "metadata": None,
            "status": "pending",
            "inserted_at": NOW,
            "updated_at": NOW,
        }
    )


@pytest_asyncio.fixture
async def transport():
    t = AsyncTransport(API, api_key="k")
    yield t
    await t.aclose()


async def test_upsert_resolves_question_name_via_record_object(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={
            "items": [
                {
                    "id": Q_SIZE,
                    "schema_id": SCHEMA_ID,
                    "name": "size",
                    "title": "Size",
                    "description": None,
                    "type": "text",
                    "columns": ["size"],
                    "settings": {},
                    "required": False,
                    "inserted_at": NOW,
                    "updated_at": NOW,
                }
            ]
        },
    )
    httpx_mock.add_response(method="PUT", url=f"{API}/api/v2/records/{RECORD_ID}/suggestions", json=_suggestion())
    questions = Questions(transport)
    suggestions = Suggestions(transport, questions)
    result = await suggestions.upsert(_record_obj(), "size", "120", score=0.9, agent="claude")
    assert str(result.question_id) == Q_SIZE
    body = json.loads(httpx_mock.get_requests()[-1].read())
    assert body["question_id"] == Q_SIZE and body["agent"] == "claude" and body["score"] == 0.9


async def test_upsert_name_without_schema_raises(transport):
    suggestions = Suggestions(transport, Questions(transport))
    with pytest.raises(ValueError, match="schema_id"):
        await suggestions.upsert(RECORD_ID, "size", "120")


async def test_upsert_accepts_question_id_directly(httpx_mock, transport):
    httpx_mock.add_response(method="PUT", url=f"{API}/api/v2/records/{RECORD_ID}/suggestions", json=_suggestion())
    suggestions = Suggestions(transport, Questions(transport))
    await suggestions.upsert(RECORD_ID, Q_SIZE, "120")  # no questions fetch needed
    assert len(httpx_mock.get_requests()) == 1


async def test_response_get_maps_null_to_none(httpx_mock, transport):
    httpx_mock.add_response(url=f"{API}/api/v2/records/{RECORD_ID}/responses", json=None)
    assert await Responses(transport).get(RECORD_ID) is None


async def test_response_get_unwraps_values(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/records/{RECORD_ID}/responses",
        json={
            "id": str(uuid.uuid4()),
            "record_id": RECORD_ID,
            "user_id": str(uuid.uuid4()),
            "values": {"size": {"value": "135"}},
            "status": "submitted",
            "inserted_at": NOW,
            "updated_at": NOW,
        },
    )
    response = await Responses(transport).get(RECORD_ID)
    assert response.unwrapped_values == {"size": "135"}


async def test_projection_get(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/projection/references/10.1000/j.abc?workspace_id={WS}",
        json={
            "reference": "10.1000/j.abc",
            "records": [
                {
                    "record_id": RECORD_ID,
                    "schema_id": SCHEMA_ID,
                    "reference": "10.1000/j.abc",
                    "cells": [{"question_name": "size", "value": "120", "source": "suggestion"}],
                }
            ],
            "total_records": 1,
        },
    )
    view = await Projections(transport).get(WS, "10.1000/j.abc")
    assert view.records[0].cells[0].source == Source.suggestion
