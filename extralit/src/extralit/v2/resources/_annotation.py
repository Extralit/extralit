from __future__ import annotations

import uuid
from typing import Any, Optional

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Response, Suggestion
from extralit.v2.resources._base import ResourceBase
from extralit.v2.resources._questions import Questions


def _as_question_id(question: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(question)))
    except (ValueError, AttributeError, TypeError):
        return None


class Suggestions(ResourceBase):
    def __init__(self, transport: AsyncTransport, questions: Questions):
        super().__init__(transport)
        self._questions = questions

    async def upsert(
        self,
        record: Any,
        question: Any,
        value: Any,
        *,
        score: Optional[Any] = None,
        agent: Optional[str] = None,
        type: Optional[str] = None,
        schema_id: Optional[Any] = None,
    ) -> Suggestion:
        """Upsert one suggestion per (record, question). Suggestions key by question ID on
        the wire, but callers may pass a question NAME — resolved via the record's schema."""
        record_id = getattr(record, "id", record)
        question_id = _as_question_id(question)
        if question_id is None:  # a name: resolve against the record's schema
            resolve_schema = getattr(record, "schema_id", None) or schema_id
            if resolve_schema is None:
                raise ValueError("resolving a question name requires a Record object or an explicit schema_id=")
            question_id = str(await self._questions.id_for(resolve_schema, question))
        body: dict = {"question_id": question_id, "value": value}
        if score is not None:
            body["score"] = score
        if agent is not None:
            body["agent"] = agent
        if type is not None:
            body["type"] = type
        payload = await self._transport.request("PUT", f"/records/{record_id}/suggestions", json=body)
        return Suggestion.model_validate(payload)

    async def list(self, record_id) -> list[Suggestion]:
        payload = await self._transport.request("GET", f"/records/{record_id}/suggestions")
        return [Suggestion.model_validate(item) for item in payload["items"]]


class Responses(ResourceBase):
    async def get(self, record_id) -> Optional[Response]:
        """GET returns literal `null` with 200 (not 404) when no response exists yet."""
        payload = await self._transport.request("GET", f"/records/{record_id}/responses")
        return None if payload is None else Response.model_validate(payload)
