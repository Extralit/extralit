from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    document_ids: list[UUID] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    pages: list[int] = Field(default_factory=list)
    kinds: list[Literal["text", "table", "figure"]] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)


class SearchScores(BaseModel):
    bm25: Optional[float] = None
    # Distance to the query vector: lower is closer.
    vector: Optional[float] = None
    rrf: float


class SearchHit(BaseModel):
    chunk_id: str
    document_id: UUID
    reference: Optional[str] = None
    kind: str
    text: str
    headings: list[str]
    item_refs: list[str]
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    scores: SearchScores


class SearchResponse(BaseModel):
    hits: list[SearchHit]
