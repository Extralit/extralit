from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from extralit.v2.models import Record, ReferenceView, SearchPage
from extralit.v2.resources._base import ResourceBase

BULK_UPSERT_MAX_ITEMS = 500  # server cap (RECORDS_BULK_UPSERT_MAX_ITEMS)
DELETE_MAX_IDS = 100  # server cap (DELETE_RECORDS_LIMIT)


def _normalize_items(items: Any, reference: Optional[str]) -> list[dict]:
    if hasattr(items, "to_dict") and hasattr(items, "columns"):  # pandas.DataFrame, kept lazy
        items = items.to_dict(orient="records")
    normalized = []
    for item in items:
        if "fields" in item:
            entry = dict(item)
        else:
            fields = dict(item)
            entry = {"fields": fields}
            if "reference" in fields:
                entry["reference"] = fields.pop("reference")
        if reference is not None:
            entry.setdefault("reference", reference)
        if "reference" not in entry:
            raise ValueError("every record needs a reference (per-item or via the reference= argument)")
        normalized.append(entry)
    return normalized


def _normalize_filters(filters: Optional[list]) -> list[dict]:
    normalized = []
    for item in filters or []:
        if isinstance(item, dict):
            normalized.append({"column": item["column"], "op": item["op"], "value": item["value"]})
        else:
            column, op, value = item
            normalized.append({"column": column, "op": op, "value": value})
    return normalized


class Records(ResourceBase):
    async def bulk_upsert(
        self,
        schema_id,
        items: Any,
        *,
        reference: Optional[str] = None,
        max_concurrency: int = 4,
        on_progress: Optional[Callable] = None,
    ) -> list[Record]:
        """Idempotent on external_id; metadata is patch-like (omitted keys preserved).
        Auto-chunks at the server's 500-item cap; chunks fly concurrently but the
        returned list preserves input order."""
        normalized = _normalize_items(items, reference)
        chunks = [normalized[i : i + BULK_UPSERT_MAX_ITEMS] for i in range(0, len(normalized), BULK_UPSERT_MAX_ITEMS)]
        results: list = [None] * len(chunks)
        total = len(normalized)
        done = 0
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run(index: int, chunk: list[dict]) -> None:
            nonlocal done
            async with semaphore:
                payload = await self._transport.request(
                    "POST", f"/schemas/{schema_id}/records:bulk-upsert", json={"items": chunk}
                )
            results[index] = payload["items"]
            done += len(chunk)
            if on_progress:
                on_progress(done, total)

        await asyncio.gather(*(_run(i, c) for i, c in enumerate(chunks)))
        return [Record.model_validate(item) for chunk in results for item in chunk]

    async def search(
        self,
        schema_id,
        *,
        text: Optional[str] = None,
        filters: Optional[list] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SearchPage:
        payload = await self._transport.request(
            "POST",
            f"/schemas/{schema_id}/records:search",
            json={"text": text, "filters": _normalize_filters(filters), "offset": offset, "limit": limit},
        )
        return SearchPage(items=[Record.model_validate(i) for i in payload["items"]], total=payload["total"])

    async def list(
        self,
        schema_id,
        *,
        offset: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> SearchPage:
        params: dict = {"offset": offset, "limit": limit}
        if status is not None:
            params["status"] = status
        if reference is not None:
            params["reference"] = reference
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/records", params=params)
        return SearchPage(items=[Record.model_validate(i) for i in payload["items"]], total=payload["total"])

    async def delete(self, schema_id, ids: list) -> None:
        id_strings = [str(record_id) for record_id in ids]
        for start in range(0, len(id_strings), DELETE_MAX_IDS):
            chunk = id_strings[start : start + DELETE_MAX_IDS]
            await self._transport.request("DELETE", f"/schemas/{schema_id}/records", params={"ids": ",".join(chunk)})

    async def get_reference(self, workspace_id, reference: str) -> ReferenceView:
        # Slashes stay raw: the server route is /references/{reference:path}.
        payload = await self._transport.request(
            "GET", f"/references/{reference}", params={"workspace_id": str(workspace_id)}
        )
        return ReferenceView.model_validate(payload)
