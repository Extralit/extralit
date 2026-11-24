"""Tests for `GET /documents/{document_id}/layout`."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, Size
from docling_core.types.doc.document import CURRENT_VERSION
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts.ocr.docling_builder import (
    LayoutBlock,
    PageContext,
    append_blocks,
    new_document,
)
from extralit_server.models.database import Document
from tests.factories import (
    AdminFactory,
    AnnotatorFactory,
    DocumentFactory,
    WorkspaceFactory,
    WorkspaceUserFactory,
)

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
    return await DocumentFactory.create(workspace=workspace, metadata_=metadata)


LAYOUT_METADATA = {
    "layout_url": "documents/doc/1.docling.json",
    "parser": "pdf_inspector",
    "docling_version": CURRENT_VERSION,
    "num_items": 4,
    "num_pages": 2,
    "pages_needing_ocr": [],
}


@pytest.fixture
def load_layout():
    with patch(
        "extralit_server.api.handlers.v1.documents.layout_storage.load_layout",
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
            "extralit_server.api.handlers.v1.documents.layout_storage.load_layout",
            new=AsyncMock(side_effect=RuntimeError("object missing")),
        ):
            response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 404

    async def test_layout_from_a_newer_docling_is_409(self, async_client: AsyncClient, db, owner_auth_header):
        from pydantic import ValidationError

        document = await make_document(db, LAYOUT_METADATA)
        error = ValidationError.from_exception_data("DoclingDocument", [])

        with patch(
            "extralit_server.api.handlers.v1.documents.layout_storage.load_layout",
            new=AsyncMock(side_effect=error),
        ):
            response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 409

    async def test_requires_authentication(self, async_client: AsyncClient, db, load_layout):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(f"/api/v1/documents/{document.id}/layout")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestDocumentLayoutAuthorization:
    """This route returns document contents, so a role check alone is not enough."""

    async def test_annotator_outside_the_workspace_is_denied(self, async_client: AsyncClient, db, load_layout):
        document = await make_document(db, LAYOUT_METADATA)
        outsider = await AnnotatorFactory.create()

        response = await async_client.get(
            f"/api/v1/documents/{document.id}/layout",
            headers={API_KEY_HEADER_NAME: outsider.api_key},
        )

        assert response.status_code == 403

    async def test_admin_outside_the_workspace_is_denied(self, async_client: AsyncClient, db, load_layout):
        document = await make_document(db, LAYOUT_METADATA)
        outsider = await AdminFactory.create()

        response = await async_client.get(
            f"/api/v1/documents/{document.id}/layout",
            headers={API_KEY_HEADER_NAME: outsider.api_key},
        )

        assert response.status_code == 403

    async def test_annotator_inside_the_workspace_is_allowed(self, async_client: AsyncClient, db, load_layout):
        workspace = await WorkspaceFactory.create(name=f"ws-{uuid4().hex[:8]}")
        document = await DocumentFactory.create(workspace=workspace, metadata_={"layout_metadata": LAYOUT_METADATA})
        member = await AnnotatorFactory.create()
        await WorkspaceUserFactory.create(workspace_id=workspace.id, user_id=member.id)

        response = await async_client.get(
            f"/api/v1/documents/{document.id}/layout",
            headers={API_KEY_HEADER_NAME: member.api_key},
        )

        assert response.status_code == 200

    async def test_owner_is_allowed_across_workspaces(
        self, async_client: AsyncClient, db, owner_auth_header, load_layout
    ):
        document = await make_document(db, LAYOUT_METADATA)

        response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 200


@pytest.mark.asyncio
class TestPageSizesFromTheStoredJson:
    async def test_page_sizes_come_from_docling_json_with_no_pages_dataset(
        self, async_client: AsyncClient, db, owner_auth_header, tmp_path, monkeypatch
    ):
        import json

        from extralit_server.contexts import files
        from extralit_server.contexts.ocr import storage as layout_storage
        from extralit_server.helpers import shared_resources

        monkeypatch.setattr(files.settings, "storage_url", tmp_path.as_uri())
        storage = files.ObjectStorage()
        monkeypatch.setitem(shared_resources, "storage", storage)
        document = await make_document(db, None)
        workspace = await document.awaitable_attrs.workspace
        key = layout_storage.layout_object_path(document.id)
        await files.put_object(storage, workspace.name, key, json.dumps(build_layout().export_to_dict()))
        document.metadata_ = {"layout_metadata": {**LAYOUT_METADATA, "layout_url": key}}
        await db.commit()

        with patch.object(layout_storage, "load_layout", wraps=layout_storage.load_layout) as load:
            response = await async_client.get(f"/api/v1/documents/{document.id}/layout", headers=owner_auth_header)

        assert response.status_code == 200, response.json()
        assert response.json()["pages"] == [
            {"page_no": 1, "width": PAGE_WIDTH, "height": PAGE_HEIGHT},
            {"page_no": 2, "width": PAGE_WIDTH, "height": PAGE_HEIGHT},
        ]
        assert load.await_count == 1
        assert not (tmp_path / workspace.name / "layout" / "pages.lance").exists()
