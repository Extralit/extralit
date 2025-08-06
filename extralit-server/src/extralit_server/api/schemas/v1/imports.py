# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from uuid import UUID
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

from extralit_server.api.schemas.v1.documents import DocumentCreate


class ImportStatus(str, Enum):
    """Status of a document in the import process."""

    ADD = "add"
    UPDATE = "update"
    SKIP = "skip"
    FAILED = "failed"


class FileInfo(BaseModel):
    """Information about a file to be imported."""

    filename: str = Field(..., description="Name of the file")
    size: Optional[int] = Field(None, description="File size in bytes for comparison")


class DocumentMetadata(BaseModel):
    """Metadata information for a document to be imported."""

    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[FileInfo] = Field(default_factory=list, description="PDF file metadata (not contents)")


class ImportAnalysisRequest(BaseModel):
    """Request schema for import analysis."""

    workspace_id: UUID = Field(..., description="Target workspace ID")
    documents: Dict[str, DocumentMetadata] = Field(..., description="Reference key to file metadata mapping")


class DataframeField(BaseModel):
    """Schema definition for a dataframe field."""

    name: str = Field(..., description="Field name")
    type: str = Field(..., description="Field type (string, integer, float, boolean)")


class DataframeSchema(BaseModel):
    """Schema definition for tabular dataframe structure."""

    fields: List[DataframeField] = Field(..., description="List of field definitions")
    primaryKey: List[str] = Field(..., description="Primary key field names")


class DataframeData(BaseModel):
    """Tabular dataframe representation for generalized import support."""

    schema: DataframeSchema = Field(..., description="Schema definition with fields and primary key")
    data: List[Dict[str, Any]] = Field(..., description="List of data rows as dictionaries")


class DocumentImportAnalysis(BaseModel):
    """Information about a document in the import analysis response."""

    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[str] = Field(default_factory=list, description="PDF filenames matched to this reference")
    status: ImportStatus = Field(..., description="Import status (add, update, skip, failed)")
    validation_errors: Optional[List[str]] = Field(default_factory=list, description="Validation error messages if any")


class ImportSummary(BaseModel):
    """Summary statistics for import analysis."""

    total_documents: int = Field(..., description="Total number of documents analyzed")
    add_count: int = Field(..., description="Number of documents to be added")
    update_count: int = Field(..., description="Number of documents to be updated")
    skip_count: int = Field(..., description="Number of documents to be skipped")
    failed_count: int = Field(..., description="Number of documents that failed analysis")


class ImportAnalysisResponse(BaseModel):
    """Response schema for import analysis."""

    documents: Dict[str, DocumentImportAnalysis] = Field(..., description="Reference key to document info mapping")
    summary: ImportSummary = Field(..., description="Import analysis summary")


class BulkDocumentInfo(BaseModel):
    """Information about a document in the bulk upload request."""

    reference: str = Field(..., description="BibTeX reference key for job tracking")
    document_create: DocumentCreate = Field(..., description="Document creation data")
    associated_files: List[str] = Field(..., description="Multiple PDF filenames for this reference")


class DocumentsBulkCreate(BaseModel):
    """Metadata for bulk document upload."""

    documents: List[BulkDocumentInfo] = Field(..., description="List of documents to upload")


class DocumentsBulkResponse(BaseModel):
    """Response schema for bulk document upload."""

    job_ids: Dict[str, str] = Field(..., description="Reference key to job_id mapping for frontend tracking")
    total_documents: int = Field(..., description="Total number of documents in the request")
    failed_validations: List[str] = Field(default_factory=list, description="Files that failed validation")


class ImportHistoryCreate(BaseModel):
    """Request schema for creating import history record."""

    workspace_id: UUID = Field(..., description="Target workspace ID")
    filename: str = Field(..., description="Import filename (.bib, .csv, etc.)")
    data: Dict[str, Any] = Field(..., description="Tabular dataframe data converted from BibTeX file")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Import metadata including ImportStatus and associated files for each reference"
    )


class ImportHistoryResponse(BaseModel):
    """Response schema for import history creation and retrieval."""

    id: UUID = Field(..., description="Import history record ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    username: str = Field(..., description="Username who created the import")
    filename: str = Field(..., description="Import filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    data: Optional[Dict[str, Any]] = Field(None, description="Tabular dataframe data (only in detailed view)")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Import metadata with status and files (in list and detailed view)"
    )


class ImportHistoryCreateResponse(BaseModel):
    """Response schema for import history creation (without user object)."""

    id: UUID = Field(..., description="Import history record ID")
    workspace_id: UUID = Field(..., description="Workspace ID")
    filename: str = Field(..., description="Import filename")
    created_at: datetime = Field(..., description="Creation timestamp")
