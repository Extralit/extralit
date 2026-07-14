from __future__ import annotations

from typing import Any, Optional

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Schema, SchemaVersion
from extralit.v2.resources._base import ResourceBase


class Schemas(ResourceBase):
    def __init__(self, transport: AsyncTransport):
        super().__init__(transport)
        self._version_cache: dict = {}  # (schema_id, version) -> SchemaVersion; versions are immutable

    async def create(self, workspace_id, name: str, settings: Optional[dict] = None) -> Schema:
        payload = await self._transport.request(
            "POST",
            "/schemas",
            json={"name": name, "workspace_id": str(workspace_id), "settings": settings or {}},
        )
        return Schema.model_validate(payload)

    async def list(self, workspace_id) -> list[Schema]:
        payload = await self._transport.request("GET", "/schemas", params={"workspace_id": str(workspace_id)})
        return [Schema.model_validate(item) for item in payload["items"]]

    async def get(self, schema_id) -> Schema:
        return Schema.model_validate(await self._transport.request("GET", f"/schemas/{schema_id}"))

    async def get_by_name(self, workspace_id, name: str) -> Schema:
        for schema in await self.list(workspace_id):
            if schema.name == name:
                return schema
        raise NotFoundError(404, f"schema named {name!r} not found in workspace {workspace_id}")

    async def update(self, schema_id, *, name: Optional[str] = None, settings: Optional[dict] = None) -> Schema:
        body: dict = {}
        if name is not None:
            body["name"] = name
        if settings is not None:
            body["settings"] = settings
        return Schema.model_validate(await self._transport.request("PUT", f"/schemas/{schema_id}", json=body))

    async def publish(self, schema_id, schema: Any, review_widgets: Optional[dict] = None) -> SchemaVersion:
        """Publish a new schema version. `schema` is a pandera DataFrameSchema (anything with
        .to_json()) or the already-serialized JSON string. review_widgets ride out-of-band
        because pandera's to_json() drops Column.metadata."""
        body = schema.to_json() if hasattr(schema, "to_json") else schema
        payload = await self._transport.request(
            "POST",
            f"/schemas/{schema_id}/versions",
            json={"body": body, "review_widgets": review_widgets or {}},
        )
        version = SchemaVersion.model_validate(payload)
        self._version_cache[(str(schema_id), version.version)] = version
        return version

    async def versions(self, schema_id) -> list[SchemaVersion]:
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/versions")
        return [SchemaVersion.model_validate(item) for item in payload]

    async def get_version(self, schema_id, version: int) -> SchemaVersion:
        key = (str(schema_id), version)
        if key not in self._version_cache:
            payload = await self._transport.request("GET", f"/schemas/{schema_id}/versions/{version}")
            self._version_cache[key] = SchemaVersion.model_validate(payload)
        return self._version_cache[key]

    async def columns(self, schema_id) -> list[dict]:
        return await self._transport.request("GET", f"/schemas/{schema_id}/columns")
