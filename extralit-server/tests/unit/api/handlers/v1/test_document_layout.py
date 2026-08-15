"""Tests for `GET /documents/{document_id}/layout`."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size
from docling_core.types.doc.document import CURRENT_VERSION
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    new_document,
)
from extralit_server.models.database import Document
from tests.factories import DocumentFactory, WorkspaceFactory

PAGE_WIDTH, PAGE_HEIGHT = 612.0, 792.0


def bbox(t: float, b: float, left: float = 10.0, right: float = 100.0) -> BoundingBox:
    return BoundingBox(l=left, t=t, r=right, b=b, coord_origin=CoordOrigin.TOPLEFT)


def build_layout():
    doc = new_document("sample")
    append_blocks(
        doc,
        PageContext(page_no=1, size=Size(width=PAGE_WIDTH, height=PAGE_HEIGHT)),
        [
            LayoutBlock(label=DocItemLabel.SECTION_HEADER, bbox=bbox(t=10, b=40), text="Methods", level=2),
            LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=50, b=90), text="Body text."),
            LayoutBlock(label=DocItemLabel.TABLE, bbox=bbox(t=200, b=400)),
        ],
    )
    append_blocks(
        doc,
        PageContext(page_no=2, size=Size(width=PAGE_WIDTH, height=PAGE_HEIGHT)),
        [LayoutBlock(label=DocItemLabel.TEXT, bbox=bbox(t=10, b=30), text="Page two.")],
    )
    return doc


async def make_document(db: AsyncSession, layout_metadata: dict | None) -> Document:
    workspace = await WorkspaceFactory.create(name=f"ws-{uuid4().hex[:8]}")
    metadata = {"layout_metadata": layout_metadata} if layout_metadata else {}
    return await DocumentFactory.create(workspace_id=workspace.id, metadata_=metadata)


LAYOUT_METADATA = {
    "layout_url": "layout/doc.docling.json",
    "parser": "pdf_inspector",
    "docling_version": CURRENT_VERSION,
    "num_items": 4,
    "num_pages": 2,
    "pages_needing_ocr": [],
}


@pytest.fixture
def load_layout():
    with patch(
        "extralit_server.api.handlers.v1.documents.storage.load_layout",
        new=AsyncMock(return_value=build_layout()),
    ) as mock:
        yield mock


@pytest.mark.asyncio
class TestGetDocumentLayout:
    async def test_returns_the_projected_layout(self, async_client: AsyncClient, db, owner_auth_header, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 200
        body = response.json()
        assert body["document_id"] == str(document.id)
        assert body["docling_version"] == CURRENT_VERSION
        assert body["num_items"] == 4
        assert body["num_pages"] == 2

    async def test_items_carry_the_full_provenance_triple(
        self, async_client: AsyncClient, db, owner_auth_header, load_layout
    ):
        document = await make_document(db, LAYOUT_METADATA)

        body = (await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)).json()

        for item in body["items"]:
            for prov in item["prov"]:
                assert prov["page_no"] >= 1
                assert set(prov["bbox"]) >= {"l", "t", "r", "b", "coord_origin"}
                assert len(prov["charspan"]) == 2

    async def test_self_ref_is_returned_as_the_citation_anchor(
        self, async_client: AsyncClient, db, owner_auth_header, load_layout
    ):
        document = await make_document(db, LAYOUT_METADATA)

        body = (await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)).json()

        assert all(item["self_ref"].startswith("#/") for item in body["items"])

    async def test_items_are_in_reading_order(self, async_client: AsyncClient, db, owner_auth_header, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        body = (await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)).json()

        orders = [item["reading_order"] for item in body["items"]]
        assert orders == sorted(orders)

    async def test_pages_carry_their_geometry(self, async_client: AsyncClient, db, owner_auth_header, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        body = (await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)).json()

        assert [p["page_no"] for p in body["pages"]] == [1, 2]
        assert body["pages"][0]["height"] == PAGE_HEIGHT

    async def test_heading_level_is_exposed(self, async_client: AsyncClient, db, owner_auth_header, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        body = (await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)).json()

        heading = next(i for i in body["items"] if i["label"] == "section_header")
        assert heading["level"] == 2

    async def test_pages_filter_narrows_the_response(
        self, async_client: AsyncClient, db, owner_auth_header, load_layout
    ):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(
            f"/api/v1/documents/{document.id}/layout", params={"pages": [2]}, headers=owner_auth_header
        )

        body = response.json()
        assert [p["page_no"] for p in body["pages"]] == [2]
        assert {prov["page_no"] for i in body["items"] for prov in i["prov"]} == {2}

    async def test_labels_filter_narrows_the_response(
        self, async_client: AsyncClient, db, owner_auth_header, load_layout
    ):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(
            f"/api/v1/documents/{document.id}/layout", params={"labels": ["table"]}, headers=owner_auth_header
        )

        body = response.json()
        assert [i["label"] for i in body["items"]] == ["table"]

    async def test_missing_document_is_404(self, async_client: AsyncClient, owner_auth_header):
        response = await async_client.get(f"/api/v1/documents/{uuid4()}/layout", headers=owner_auth_header)

        assert response.status_code == 404

    async def test_document_without_extracted_layout_is_404(self, async_client: AsyncClient, db, owner_auth_header):
        document = await make_document(db, layout_metadata=None)

        response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 404
        assert "No layout" in response.json()["detail"]

    async def test_unreadable_stored_layout_is_404(self, async_client: AsyncClient, db, owner_auth_header):
        document = await make_document(db, LAYOUT_METADATA)

        with patch(
            "extralit_server.api.handlers.v1.documents.storage.load_layout",
            new=AsyncMock(side_effect=RuntimeError("object missing")),
        ):
            response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 404

    async def test_layout_from_a_newer_docling_is_409(self, async_client: AsyncClient, db, owner_auth_header):
        from pydantic import ValidationError

        document = await make_document(db, LAYOUT_METADATA)
        error = ValidationError.from_exception_data("DoclingDocument", [])

        with patch(
            "extralit_server.api.handlers.v1.documents.storage.load_layout",
            new=AsyncMock(side_effect=error),
        ):
            response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 409

    async def test_requires_authentication(self, async_client: AsyncClient, db, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(f"/api/v1/documents/{document.id}/layout")

        assert response.status_code == 401
