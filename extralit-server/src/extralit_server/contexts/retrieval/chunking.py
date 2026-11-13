"""One chunk per body `DocItem` of a `DoclingDocument`.

Text comes from docling's markdown serializers, which already prefix a table or picture with its
linked caption and render tables with a header row. Nothing is split; the embedder truncates.
"""

from __future__ import annotations

from collections import Counter
from importlib.metadata import version
from typing import Any, Optional

import pyarrow as pa
import xxhash
from docling_core.transforms.serializer.markdown import MarkdownDocSerializer, MarkdownParams, MarkdownTableSerializer
from docling_core.types.doc import DocItemLabel, DoclingDocument
from docling_core.types.doc.document import DocItem, FloatingItem, PictureItem, SectionHeaderItem, TableItem, TitleItem

from extralit_server.contexts.retrieval.arrow import CHUNK_SCHEMA

CHUNKER_VERSION = "item-v1"
CHUNKER_FINGERPRINT = f"{CHUNKER_VERSION}+docling-core-{version('docling-core')}"
BREADCRUMB_SEPARATOR = " > "

_MARKDOWN = MarkdownParams(escape_html=False, escape_underscores=False, image_placeholder="")


def chunk_id(document_id: str, text: str, occurrence: int) -> str:
    """Stable under insertions and deletions elsewhere: only identical earlier texts shift it."""
    return xxhash.xxh64(f"{document_id}\x00{text}\x00{occurrence}".encode()).hexdigest()


def _pages(items: list[DocItem]) -> tuple[Optional[int], Optional[int]]:
    pages = [prov.page_no for item in items for prov in item.prov]
    return (min(pages), max(pages)) if pages else (None, None)


def _kind(item: DocItem) -> str:
    if isinstance(item, TableItem):
        return "table"
    if isinstance(item, PictureItem):
        return "figure"
    return "text"


def _open_headings(stack: list[tuple[int, str]], item: DocItem) -> None:
    level = 0 if isinstance(item, TitleItem) else item.level
    while stack and stack[-1][0] >= level:
        stack.pop()
    if item.text.strip():
        stack.append((level, item.text.strip()))


def chunk_document(doc: DoclingDocument, document_id: str, reference: Optional[str] = None) -> pa.Table:
    """Chunk `doc` in reading order into rows matching `CHUNK_SCHEMA`."""
    serializer = MarkdownDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer(), params=_MARKDOWN)
    document_id = str(document_id)
    seen: Counter[str] = Counter()
    headings: list[tuple[int, str]] = []
    rows: list[dict[str, Any]] = []

    for item, _depth in doc.iterate_items(with_groups=False):
        if isinstance(item, (SectionHeaderItem, TitleItem)) and item.label in (
            DocItemLabel.SECTION_HEADER,
            DocItemLabel.TITLE,
        ):
            _open_headings(headings, item)
            continue
        if not isinstance(item, DocItem):
            continue

        # A caption linked to its owner serializes as '' and an uncaptioned picture likewise.
        text = serializer.serialize(item=item).text.strip()
        if not text:
            continue

        members = [item]
        if isinstance(item, FloatingItem):
            members += [ref.resolve(doc) for ref in item.captions]
        start, end = _pages(members)
        breadcrumb = [title for _level, title in headings]
        embed_text = f"{BREADCRUMB_SEPARATOR.join(breadcrumb)}\n\n{text}" if breadcrumb else text

        rows.append(
            {
                "chunk_id": chunk_id(document_id, text, seen[text]),
                "document_id": document_id,
                "reference": reference,
                "ordinal": len(rows),
                "kind": _kind(item),
                "text": text,
                "embed_text": embed_text,
                "headings": breadcrumb,
                "item_refs": [member.self_ref for member in members],
                "page_start": start,
                "page_end": end,
                "chunker_fingerprint": CHUNKER_FINGERPRINT,
            }
        )
        seen[text] += 1

    return pa.Table.from_pylist(rows, schema=CHUNK_SCHEMA)
