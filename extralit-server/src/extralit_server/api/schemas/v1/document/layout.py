"""Wire schema for extracted document layout.

A flat projection of `DoclingDocument`, structurally identical to its `ProvenanceItem` /
`BoundingBox` and to `ITEM_SCHEMA` in `contexts.ocr.arrow`. Deliberately not the raw
`DoclingDocument` — its 73 recursive `$defs` would make the OpenAPI schema and any
hand-written frontend types unusable.
"""

from typing import Optional

from pydantic import BaseModel, Field


class BoundingBoxOut(BaseModel):
    """A rectangle in page points."""

    # Field names mirror docling's BoundingBox exactly — renaming would break the contract.
    l: float = Field(..., description="Left edge")  # noqa: E741
    t: float = Field(..., description="Top edge")
    r: float = Field(..., description="Right edge")
    b: float = Field(..., description="Bottom edge")
    coord_origin: str = Field(default="TOPLEFT", description="Origin the coordinates are measured from")


class ProvenanceOut(BaseModel):
    """Where an item came from: the page, the region, and the span of its own text."""

    page_no: int = Field(..., description="1-indexed page number")
    bbox: BoundingBoxOut = Field(..., description="Region on the page")
    charspan: tuple[int, int] = Field(..., description="Item-local character span, not a document offset")


class LayoutItemOut(BaseModel):
    """One layout element, anchored by `self_ref`."""

    self_ref: str = Field(..., description="Citation anchor, e.g. `#/texts/12`")
    parent_ref: Optional[str] = Field(None, description="Reference of the parent node")
    label: str = Field(..., description="DocItemLabel, e.g. `text`, `table`, `picture`")
    content_layer: Optional[str] = Field(None, description="Content layer, e.g. `body` or `furniture`")
    level: Optional[int] = Field(None, description="Heading level, when the item is a section header")
    reading_order: int = Field(..., description="Position in document reading order")
    text: Optional[str] = Field(None, description="Item text, when it has any")
    html: Optional[str] = Field(None, description="Rendered HTML, for tables")
    prov: list[ProvenanceOut] = Field(default_factory=list, description="One entry per page region")


class LayoutPageOut(BaseModel):
    """Page geometry every bbox on that page is relative to."""

    page_no: int = Field(..., description="1-indexed page number")
    width: float = Field(..., description="Page width in points")
    height: float = Field(..., description="Page height in points")


class DocumentLayoutOut(BaseModel):
    """Extracted layout for one document."""

    document_id: str = Field(..., description="Document ID")
    docling_version: str = Field(..., description="docling-core schema version of the stored document")
    num_items: int = Field(..., description="Number of items in this response")
    num_pages: int = Field(..., description="Number of pages in this response")
    pages: list[LayoutPageOut] = Field(default_factory=list, description="Page geometry")
    items: list[LayoutItemOut] = Field(default_factory=list, description="Layout items in reading order")
