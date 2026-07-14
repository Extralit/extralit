from __future__ import annotations

from uuid import UUID

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Question
from extralit.v2.resources._base import ResourceBase


class Questions(ResourceBase):
    """Callers address questions by NAME; the server keys suggestions by question ID
    (cells/response values key by name). This resource owns that join via a cached map."""

    def __init__(self, transport: AsyncTransport):
        super().__init__(transport)
        self._maps: dict = {}  # str(schema_id) -> {name: UUID}

    async def list(self, schema_id) -> list[Question]:
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/questions")
        items = [Question.model_validate(item) for item in payload["items"]]
        self._maps[str(schema_id)] = {q.name: q.id for q in items}
        return items

    async def get(self, question_id) -> Question:
        return Question.model_validate(await self._transport.request("GET", f"/questions/{question_id}"))

    async def id_for(self, schema_id, name: str) -> UUID:
        key = str(schema_id)
        if key not in self._maps or name not in self._maps[key]:
            await self.list(schema_id)  # refetch once: the question may be newly created
        if name not in self._maps.get(key, {}):
            raise NotFoundError(404, f"question named {name!r} not found in schema {schema_id}")
        return self._maps[key][name]

    def invalidate(self, schema_id) -> None:
        self._maps.pop(str(schema_id), None)
