"""Tests for the serialized read-modify-write of `documents.metadata_`."""

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata, LayoutMetadata
from extralit_server.contexts.document.metadata import update_processing_metadata
from extralit_server.models.database import Document
from tests.factories import DocumentFactory, WorkspaceFactory


def _layout(parser: str = "pdf_inspector") -> LayoutMetadata:
    return LayoutMetadata(layout_url="layout/x.docling.json", parser=parser, docling_version="1.7.0")


@pytest.mark.asyncio
class TestUpdateProcessingMetadata:
    async def test_locks_the_row_before_reading(self, db: AsyncSession, mocker):
        workspace = await WorkspaceFactory.create()
        document = await DocumentFactory.create(workspace=workspace)
        statements = []
        original = db.execute

        async def record(statement, *args, **kwargs):
            statements.append(str(statement))
            return await original(statement, *args, **kwargs)

        mocker.patch.object(db, "execute", side_effect=record)

        await update_processing_metadata(db, document.id, lambda m: setattr(m, "workflow_status", "done"))

        assert any("FOR UPDATE" in statement for statement in statements)

    async def test_keeps_keys_written_since_this_session_last_read(self, db: AsyncSession):
        workspace = await WorkspaceFactory.create()
        document = await DocumentFactory.create(workspace=workspace)
        await db.get(Document, document.id)  # this session now holds a stale copy

        await db.execute(
            update(Document)
            .where(Document.id == document.id)
            .values(metadata_=DocumentProcessingMetadata(layout_metadata=_layout()).model_dump())
        )

        metadata = await update_processing_metadata(
            db, document.id, lambda m: setattr(m, "workflow_status", "completed")
        )

        assert metadata.layout_metadata is not None
        assert metadata.workflow_status == "completed"

    async def test_returns_none_when_the_document_is_gone(self, db: AsyncSession):
        from uuid import uuid4

        assert await update_processing_metadata(db, uuid4(), lambda m: None) is None
