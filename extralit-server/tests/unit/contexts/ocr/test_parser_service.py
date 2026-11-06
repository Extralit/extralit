"""Tests for the parser service: routing (plan) and per-page merging (parse)."""

from collections.abc import Sequence
from typing import Optional

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, DoclingDocument, Size

from extralit_server.api.schemas.v1.document.metadata import TriageMetadata
from extralit_server.contexts.ocr.docling_builder import LayoutBlock
from extralit_server.contexts.ocr.parsers.service import (
    ParsePlan,
    ParserService,
    ParseTask,
    build_document,
)

PAGE = Size(width=100.0, height=200.0)


def _box(top: float, left: float, size: float = 10.0) -> BoundingBox:
    return BoundingBox(l=left, t=top, r=left + size, b=top + size, coord_origin=CoordOrigin.TOPLEFT)


def _text(top: float, left: float, text: str) -> LayoutBlock:
    return LayoutBlock(label=DocItemLabel.TEXT, bbox=_box(top, left), text=text)


class FakeParser:
    """Records what it was asked for and answers with canned blocks per page."""

    def __init__(self, blocks: Optional[dict[int, list[LayoutBlock]]] = None):
        self.blocks = blocks or {}
        self.calls: list[tuple[tuple[int, ...], bool]] = []

    def parse_pages(self, pdf_bytes: bytes, pages: Sequence[int], *, ocr: bool) -> dict[int, list[LayoutBlock]]:
        self.calls.append((tuple(pages), ocr))
        return {p: list(self.blocks.get(p, [])) for p in pages}


def _service(parsers: dict, triage: TriageMetadata, page_count: int = 3) -> ParserService:
    return ParserService(
        parsers,
        triage=lambda _: triage,
        page_sizes=lambda _: dict.fromkeys(range(1, page_count + 1), PAGE),
    )


class TestPlan:
    def test_scanned_pages_go_to_liteparse_with_ocr(self):
        triage = TriageMetadata(pdf_type="mixed", page_count=3, pages_needing_ocr=[2])
        service = _service({"pymupdf": FakeParser(), "liteparse": FakeParser()}, triage)

        plan = service.plan(b"%PDF")

        assert plan.tasks == (
            ParseTask(pages=(1, 3), parser="pymupdf", ocr=False),
            ParseTask(pages=(2,), parser="liteparse", ocr=True),
        )

    def test_digital_pages_go_to_pymupdf_when_installed(self):
        triage = TriageMetadata(pdf_type="text_based", page_count=2)
        service = _service({"pymupdf": FakeParser(), "liteparse": FakeParser()}, triage, page_count=2)

        plan = service.plan(b"%PDF")

        assert plan.tasks == (ParseTask(pages=(1, 2), parser="pymupdf", ocr=False),)

    def test_digital_pages_fall_back_to_liteparse_without_ocr(self):
        triage = TriageMetadata(pdf_type="text_based", page_count=2)
        service = _service({"liteparse": FakeParser()}, triage, page_count=2)

        plan = service.plan(b"%PDF")

        assert plan.tasks == (ParseTask(pages=(1, 2), parser="liteparse", ocr=False),)

    def test_fully_scanned_pdf_is_one_ocr_task(self):
        triage = TriageMetadata(pdf_type="image_based", page_count=2, pages_needing_ocr=[1, 2])
        service = _service({"pymupdf": FakeParser(), "liteparse": FakeParser()}, triage, page_count=2)

        plan = service.plan(b"%PDF")

        assert plan.tasks == (ParseTask(pages=(1, 2), parser="liteparse", ocr=True),)

    def test_page_count_comes_from_the_pdf_when_triage_is_unknown(self):
        triage = TriageMetadata(pdf_type="unknown")
        service = _service({"liteparse": FakeParser()}, triage, page_count=4)

        plan = service.plan(b"%PDF")

        assert plan.tasks == (ParseTask(pages=(1, 2, 3, 4), parser="liteparse", ocr=False),)

    def test_pages_allowlist_restricts_the_plan(self):
        triage = TriageMetadata(pdf_type="mixed", page_count=3, pages_needing_ocr=[2])
        service = _service({"pymupdf": FakeParser(), "liteparse": FakeParser()}, triage)

        plan = service.plan(b"%PDF", pages=[2, 3])

        assert plan.tasks == (
            ParseTask(pages=(3,), parser="pymupdf", ocr=False),
            ParseTask(pages=(2,), parser="liteparse", ocr=True),
        )

    def test_plan_summaries(self):
        plan = ParsePlan(
            tasks=(
                ParseTask(pages=(1, 3), parser="pymupdf", ocr=False),
                ParseTask(pages=(2,), parser="liteparse", ocr=True),
            )
        )

        assert plan.pages_by_parser == {"pymupdf": [1, 3], "liteparse": [2]}
        assert plan.ocr_pages == [2]


class TestParse:
    def test_each_task_runs_on_its_parser_with_its_ocr_flag(self):
        pymupdf, liteparse = FakeParser(), FakeParser()
        service = _service({"pymupdf": pymupdf, "liteparse": liteparse}, TriageMetadata(pdf_type="mixed"))
        plan = ParsePlan(
            tasks=(
                ParseTask(pages=(1, 3), parser="pymupdf", ocr=False),
                ParseTask(pages=(2,), parser="liteparse", ocr=True),
            )
        )

        service.parse(b"%PDF", plan, name="doc")

        assert pymupdf.calls == [((1, 3), False)]
        assert liteparse.calls == [((2,), True)]

    def test_blocks_from_different_tasks_merge_per_page_in_reading_order(self):
        first = FakeParser({1: [_text(50, 0, "middle"), _text(10, 0, "top")]})
        second = FakeParser({1: [_text(50, 20, "middle-right"), _text(90, 0, "bottom")]})
        service = _service({"a": first, "b": second}, TriageMetadata(pdf_type="mixed"))
        plan = ParsePlan(
            tasks=(
                ParseTask(pages=(1,), parser="a", ocr=False),
                ParseTask(pages=(1,), parser="b", ocr=False, bbox=_box(0, 0, size=200)),
            )
        )

        doc = service.parse(b"%PDF", plan, name="doc")

        assert [t.text for t in doc.texts] == ["top", "middle", "middle-right", "bottom"]

    def test_region_task_keeps_only_blocks_inside_its_bbox(self):
        parser = FakeParser({1: [_text(10, 10, "inside"), _text(150, 10, "outside"), _text(45, 10, "straddling")]})
        service = _service({"a": parser}, TriageMetadata(pdf_type="mixed"))
        region = BoundingBox(l=0, t=0, r=100, b=50, coord_origin=CoordOrigin.TOPLEFT)
        plan = ParsePlan(tasks=(ParseTask(pages=(1,), parser="a", ocr=False, bbox=region),))

        doc = service.parse(b"%PDF", plan, name="doc")

        assert [t.text for t in doc.texts] == ["inside"]

    def test_unknown_parser_in_plan_raises(self):
        service = _service({"a": FakeParser()}, TriageMetadata(pdf_type="mixed"))
        plan = ParsePlan(tasks=(ParseTask(pages=(1,), parser="nope", ocr=False),))

        with pytest.raises(ValueError, match="nope"):
            service.parse(b"%PDF", plan, name="doc")


class TestBuildDocument:
    def test_pages_are_registered_with_their_size_and_blocks_carry_provenance(self):
        blocks = {1: [_text(10, 0, "one")], 2: [_text(20, 0, "two")]}

        doc = build_document(blocks, page_sizes={1: PAGE, 2: PAGE}, name="doc", filename="doc.pdf")

        assert isinstance(doc, DoclingDocument)
        assert doc.name == "doc"
        assert doc.origin.filename == "doc.pdf"
        assert doc.pages[2].size == PAGE
        assert [(t.text, t.prov[0].page_no) for t in doc.texts] == [("one", 1), ("two", 2)]

    def test_empty_pages_are_still_registered(self):
        doc = build_document({}, page_sizes={1: PAGE}, name="doc")

        assert set(doc.pages) == {1}
        assert doc.texts == []
