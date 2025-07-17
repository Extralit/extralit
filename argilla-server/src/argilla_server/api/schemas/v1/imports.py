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
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from argilla_server.api.schemas.v1.documents import DocumentCreate


class ImportStatus(str, Enum):
    """Status of a document in the import process."""

    ADD = "add"
    UPDATE = "update"
    SKIP = "skip"
    FAILED = "failed"


class FileInfo(BaseModel):
    """Information about a file to be imported."""

    filename: str = Field(..., description="Name of the file")
    size: int = Field(..., description="File size in bytes for comparison")


class FileMetadataInfo(BaseModel):
    """Metadata information for a document to be imported."""

    document_create: DocumentCreate = Field(..., description="Document creation data")
    title: str = Field(..., description="Document title for display")
    authors: List[str] = Field(default_factory=list, description="Document authors for display")
    year: Optional[int] = Field(None, description="Publication year for display")
    venue: Optional[str] = Field(None, description="Publication venue (journal, publisher, or institution)")
    associated_files: List[FileInfo] = Field(default_factory=list, description="PDF file metadata (not contents)")


class ImportAnalysisRequest(BaseModel):
    """Request schema for import analysis."""

    workspace_id: UUID = Field(..., description="Target workspace ID")
    documents: Dict[str, FileMetadataInfo] = Field(..., description="Reference key to file metadata mapping")


class ImportDocumentInfo(BaseModel):
    """Information about a document in the import analysis response."""

    document_create: DocumentCreate = Field(..., description="Document creation data")
    title: str = Field(..., description="Document title for display")
    authors: Optional[List[str]] = Field(default_factory=list, description="Document authors for display")
    year: Optional[int] = Field(None, description="Publication year for display")
    venue: Optional[str] = Field(None, description="Publication venue (journal, publisher, or institution)")
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

    documents: Dict[str, ImportDocumentInfo] = Field(..., description="Reference key to document info mapping")
    summary: ImportSummary = Field(..., description="Import analysis summary")
