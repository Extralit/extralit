"""Route a PDF's pages to parsers and merge what they return into one `DoclingDocument`.

Routing rule: pages triage flags as needing OCR go to liteparse with OCR on; every other page
goes to pymupdf when the extra is installed, else to liteparse with OCR off. pdf_inspector is
never chosen automatically. A task may carry a `bbox`, in which case it is a region task and
only blocks mostly inside that region are kept. Each parser's own reading order is kept; blocks
from a later task on the same page are slotted in by position (see `merge_blocks`).
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
    flip_to_top_left,
    new_document,
    register_page,
)
from extralit_server.contexts.ocr.parsers.pdf_inspector import page_sizes as _page_sizes
from extralit_server.contexts.ocr.triage import triage_pdf

OCR_PARSER = "liteparse"
DIGITAL_PARSER = "pymupdf"

#: Triage reason for a page that already has a (hidden) text layer.
TEXT_LAYER_REASON = "invisible_text_layer"


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
    #: Triage's full OCR-needed list, regardless of the page allowlist.
    pages_needing_ocr: tuple[int, ...] = ()
    #: OCR-planned pages that already carry a text layer, which liteparse reads without running OCR.
    text_layer_pages: tuple[int, ...] = ()

    @property
    def pages_by_parser(self) -> dict[str, list[int]]:
        pages: dict[str, set[int]] = defaultdict(set)
        for task in self.tasks:
            pages[task.parser].update(task.pages)
        return {name: sorted(p) for name, p in pages.items()}

    @property
    def planned_ocr_pages(self) -> list[int]:
        return sorted({p for task in self.tasks if task.ocr for p in task.pages})

    @property
    def ocr_pages(self) -> list[int]:
        """Pages where OCR actually runs: planned, minus those whose text layer is read instead."""
        return [p for p in self.planned_ocr_pages if p not in set(self.text_layer_pages)]

    @property
    def ocr_skipped_pages(self) -> list[int]:
        return [p for p in self.planned_ocr_pages if p in set(self.text_layer_pages)]


def _top_left_box(block: LayoutBlock, height: float) -> BoundingBox:
    return flip_to_top_left(block.bbox, height)


def _position(block: LayoutBlock, height: float) -> tuple[float, float]:
    box = _top_left_box(block, height)
    return (box.t, box.l)


def merge_blocks(base: Sequence[LayoutBlock], extra: Sequence[LayoutBlock], height: float) -> list[LayoutBlock]:
    """Slot `extra` into `base` by `(top, left)`, keeping each list's own internal order."""
    merged = list(base)
    cursor = 0
    for block in extra:
        key = _position(block, height)
        index = next((i for i in range(cursor, len(merged)) if _position(merged[i], height) > key), len(merged))
        merged.insert(index, block)
        cursor = index + 1
    return merged


def build_document(
    blocks: Mapping[int, Sequence[LayoutBlock]],
    *,
    page_sizes: Mapping[int, Size],
    name: str,
    filename: Optional[str] = None,
    binary_hash: Optional[int] = None,
) -> DoclingDocument:
    """Lay per-page blocks into a fresh `DoclingDocument`, in the order given; every known page is registered."""
    doc = new_document(name, filename=filename, binary_hash=binary_hash)
    for page_no in sorted(page_sizes):
        ctx = PageContext(page_no=page_no, size=page_sizes[page_no])
        page_blocks = blocks.get(page_no, ())
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

    def plan(
        self,
        pdf_bytes: bytes,
        *,
        pages: Optional[Sequence[int]] = None,
        parser: Optional[str] = None,
    ) -> ParsePlan:
        """Route pages to parsers; `parser` forces one parser for every page (liteparse still OCRs flagged pages)."""
        triage = self._triage(pdf_bytes)
        page_count = triage.page_count or len(self._page_sizes(pdf_bytes))
        allowed = None if pages is None else set(pages)
        wanted = [p for p in range(1, page_count + 1) if allowed is None or p in allowed]

        flagged = set(triage.pages_needing_ocr)
        scanned = [p for p in wanted if p in flagged]
        digital = [p for p in wanted if p not in flagged]

        if parser is not None:
            self._parser(parser)
            if parser == OCR_PARSER:
                routes = [(digital, parser, False), (scanned, parser, True)]
            else:
                routes = [(wanted, parser, False)]
        else:
            digital_parser = DIGITAL_PARSER if DIGITAL_PARSER in self._parsers else OCR_PARSER
            routes = [(digital, digital_parser, False), (scanned, OCR_PARSER, True)]

        tasks = tuple(ParseTask(pages=tuple(p), parser=name, ocr=ocr) for p, name, ocr in routes if p)
        text_layer = tuple(p for p in scanned if TEXT_LAYER_REASON in triage.ocr_reasons_by_page.get(str(p), ()))
        return ParsePlan(tasks=tasks, pages_needing_ocr=tuple(sorted(flagged)), text_layer_pages=text_layer)

    def parse(
        self,
        pdf_bytes: bytes,
        plan: ParsePlan,
        *,
        name: str,
        filename: Optional[str] = None,
    ) -> DoclingDocument:
        """Run every task and merge their blocks per page; blocking, so async callers use `to_thread`."""
        sizes = self._page_sizes(pdf_bytes)
        parsers = {task.parser: self._parser(task.parser) for task in plan.tasks}
        merged: dict[int, list[LayoutBlock]] = {}
        for task in plan.tasks:
            for page_no, blocks in parsers[task.parser].parse_pages(pdf_bytes, task.pages, ocr=task.ocr).items():
                height = sizes[page_no].height if page_no in sizes else 0.0
                if task.bbox is not None:
                    blocks = [
                        b
                        for b in blocks
                        if _top_left_box(b, height).intersection_over_self(task.bbox) >= CONTAINMENT_THRESHOLD
                    ]
                merged[page_no] = merge_blocks(merged.get(page_no, []), blocks, height)

        return build_document(
            merged,
            page_sizes=sizes,
            name=name,
            filename=filename,
            binary_hash=content_hash(pdf_bytes),
        )


__all__ = ["PageParser", "ParsePlan", "ParseTask", "ParserService", "build_document", "merge_blocks"]
