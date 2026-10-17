"""Route a PDF's pages to parsers and merge what they return into one `DoclingDocument`.

Routing rule: pages triage flags as needing OCR go to liteparse with OCR on; every other page
goes to pymupdf when the extra is installed, else to liteparse with OCR off. pdf_inspector is
never chosen automatically. A task may carry a `bbox`, in which case it is a region task and
only blocks mostly inside that region are kept.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Optional, Protocol

from docling_core.types.doc import BoundingBox, DoclingDocument, Size

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts.ocr.docling_builder import (
    CONTAINMENT_THRESHOLD,
    LayoutBlock,
    PageContext,
    append_blocks,
    content_hash,
    new_document,
    register_page,
)
from extralit_server.contexts.ocr.parsers.pdf_inspector import page_sizes as _page_sizes
from extralit_server.contexts.ocr.triage import triage_pdf

OCR_PARSER = "liteparse"
DIGITAL_PARSER = "pymupdf"


class PageParser(Protocol):
    """Parse a 1-indexed page subset into top-left-origin blocks, keyed by page number."""

    def parse_pages(self, pdf_bytes: bytes, pages: Sequence[int], *, ocr: bool) -> dict[int, list[LayoutBlock]]: ...


@dataclass(frozen=True)
class ParseTask:
    pages: tuple[int, ...]
    parser: str
    ocr: bool = False
    bbox: Optional[BoundingBox] = None


@dataclass(frozen=True)
class ParsePlan:
    tasks: tuple[ParseTask, ...]

    @property
    def pages_by_parser(self) -> dict[str, list[int]]:
        pages: dict[str, set[int]] = defaultdict(set)
        for task in self.tasks:
            pages[task.parser].update(task.pages)
        return {name: sorted(p) for name, p in pages.items()}

    @property
    def ocr_pages(self) -> list[int]:
        return sorted({p for task in self.tasks if task.ocr for p in task.pages})


def build_document(
    blocks: Mapping[int, Sequence[LayoutBlock]],
    *,
    page_sizes: Mapping[int, Size],
    name: str,
    filename: Optional[str] = None,
    binary_hash: Optional[int] = None,
) -> DoclingDocument:
    """Lay per-page blocks into a fresh `DoclingDocument`; every known page is registered."""
    doc = new_document(name, filename=filename, binary_hash=binary_hash)
    for page_no in sorted(page_sizes):
        ctx = PageContext(page_no=page_no, size=page_sizes[page_no])
        page_blocks = sorted(blocks.get(page_no, ()), key=lambda b: (b.bbox.t, b.bbox.l))
        if page_blocks:
            append_blocks(doc, ctx, page_blocks)
        else:
            register_page(doc, ctx)
    return doc


class ParserService:
    def __init__(
        self,
        parsers: Mapping[str, PageParser],
        *,
        triage: Callable[[bytes], TriageMetadata] = triage_pdf,
        page_sizes: Callable[[bytes], dict[int, Size]] = _page_sizes,
    ):
        self._parsers = dict(parsers)
        self._triage = triage
        self._page_sizes = page_sizes

    def _parser(self, name: str) -> PageParser:
        try:
            return self._parsers[name]
        except KeyError:
            raise ValueError(f"unknown page parser {name!r}; available: {sorted(self._parsers)}") from None

    def plan(self, pdf_bytes: bytes, *, pages: Optional[Sequence[int]] = None) -> ParsePlan:
        triage = self._triage(pdf_bytes)
        page_count = triage.page_count or len(self._page_sizes(pdf_bytes))
        wanted = [p for p in range(1, page_count + 1) if pages is None or p in set(pages)]

        scanned = [p for p in wanted if p in set(triage.pages_needing_ocr)]
        digital = [p for p in wanted if p not in set(scanned)]
        digital_parser = DIGITAL_PARSER if DIGITAL_PARSER in self._parsers else OCR_PARSER

        tasks: list[ParseTask] = []
        if digital:
            tasks.append(ParseTask(pages=tuple(digital), parser=digital_parser, ocr=False))
        if scanned:
            tasks.append(ParseTask(pages=tuple(scanned), parser=OCR_PARSER, ocr=True))
        return ParsePlan(tasks=tuple(tasks))

    def parse(
        self,
        pdf_bytes: bytes,
        plan: ParsePlan,
        *,
        name: str,
        filename: Optional[str] = None,
    ) -> DoclingDocument:
        """Run every task and merge their blocks per page, ordered by `(top, left)`."""
        parsers = {task.parser: self._parser(task.parser) for task in plan.tasks}
        merged: dict[int, list[LayoutBlock]] = defaultdict(list)
        for task in plan.tasks:
            for page_no, blocks in parsers[task.parser].parse_pages(pdf_bytes, task.pages, ocr=task.ocr).items():
                if task.bbox is not None:
                    blocks = [b for b in blocks if b.bbox.intersection_over_self(task.bbox) >= CONTAINMENT_THRESHOLD]
                merged[page_no].extend(blocks)

        return build_document(
            merged,
            page_sizes=self._page_sizes(pdf_bytes),
            name=name,
            filename=filename,
            binary_hash=content_hash(pdf_bytes),
        )


__all__ = ["PageParser", "ParsePlan", "ParseTask", "ParserService", "build_document"]
