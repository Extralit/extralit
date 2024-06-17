from typing import Dict, Optional, List, Any, Union, Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field, Extra

class SegmentResponse(BaseModel):
    doc_id: str | UUID
    header: str | None
    page_number: int | None
    type: str | None = Field(None, description="The type of the segment.")

    class Config:
        extra = Extra.ignore


class SegmentsResponse(BaseModel):
    items: List[SegmentResponse]
