from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from extralit_server.contexts import files


class DocumentCreate(BaseModel):
    id: UUID | None = None
    workspace_id: UUID = Field(..., description="The workspace ID where the document will be uploaded.")
    url: str | None = Field(
        None,
        description="A URL to the PDF document if it is public available online. If the `file_data` is uploaded, this field should be left empty.",
        repr=False,
    )
    reference: str = Field(..., description="Extraction reference for the document")
    file_name: str | None = Field(None, description="The name of the file.")
    pmid: str | None = Field(None, description="The PubMed ID of the document.")
    doi: str | None = Field(None, description="The DOI of the document.")
    metadata: dict | None = Field(None, description="Additional metadata for the document")


class DocumentDelete(BaseModel):
    """Query Schema for deleting a document (within a Workspace)."""

    id: UUID
    reference: str | None = Field(None, description="Extraction reference for the document")


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    reference: str | None = Field(None, description="Extraction reference for the document")
    pmid: str | None = Field(None, description="The PubMed ID of the document.")
    doi: str | None = Field(None, description="The DOI of the document.")
    file_name: str | None = Field(None, description="The name of the file.")
    url: str | None = Field(None, description="A URL to the PDF document if it is publicly available online.")
    metadata: dict | None = Field(None, description="Additional metadata for the document")


class DocumentListItem(BaseModel):
    id: UUID
    workspace_id: UUID
    url: str
    file_name: str | None
    reference: str
    pmid: str | None
    doi: str | None
    metadata: dict | None = Field(None, alias="metadata_", serialization_alias="metadata")
    thumbnail_url: str | None = Field(None, description="URL to the document thumbnail image")
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def generate_thumbnail_url(cls, data: Any):
        """Generate thumbnail URL if workspace relationship is available."""
        if hasattr(data, "__dict__"):
            try:
                if hasattr(data, "workspace") and data.workspace is not None:
                    workspace_name = data.workspace.name
                    thumbnail_object_path = files.get_thumbnail_s3_object_path(data.id)
                    thumbnail_url = files.get_proxy_document_url(workspace_name, thumbnail_object_path)

                    if not hasattr(data, "thumbnail_url") or data.thumbnail_url is None:
                        data.thumbnail_url = thumbnail_url
            except Exception:
                pass

        return data
