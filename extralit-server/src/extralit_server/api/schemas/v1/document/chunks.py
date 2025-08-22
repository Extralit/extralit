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

import uuid
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, validator

"""
This is deprecated code that is outdated and should be used for reference only.
We may want to switch to using LlamaIndexDocument or other document models in the future.
"""


class Segments(BaseModel):
    items: list[Union["TextSegment", "TableSegment", "FigureSegment"]] = Field(
        default_factory=list,
        description="List of segments in the reading order of the document",
    )

    def get(self, id: str, header: str | None = None, default=None):
        for item in self.items:
            if item.id == id or (header and item.header == header):
                return item

        return default

    def __repr_str__(self, join_str: str) -> str:
        return "\n  " + f"{join_str}\n  ".join(f"{type(item).__name__}({item})" for item in self.items)

    @validator("items", pre=True, each_item=True)
    def parse_segments(cls, v):
        if not isinstance(v, dict):
            v = v.dict()

        segment_type = v.get("type", "").lower()
        if segment_type in {"figure", "image"}:
            return FigureSegment(**v)
        elif segment_type == "table" or "html" in v:
            return TableSegment(**v)
        else:
            return TextSegment(**v)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)


class Coordinates(BaseModel):
    points: list[list[float]] = Field(
        ..., description="List of 4 points, e.g. [[x1, y1], [x2, y1], [x1, y2], [x2, y2]]"
    )
    layout_width: int | None = Field(None, description="Width of the layout")
    layout_height: int | None = Field(None, description="Height of the layout")
    system: str | None = Field(description="System of coordinates")

    def __repr_str__(self, join_str: str) -> str:
        return ""


class TextSegment(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique identifier of the segment", repr=False
    )

    header: str | None = Field(
        None,
        description="Header of the element",
    )
    text: str = Field(..., description="Content as plain text", repr=False)
    summary: str | None = Field(None, description="Summary of the content")
    page_number: int | None = Field(None, description="Page number of the segment")
    coordinates: Optional["Coordinates"] = Field(
        None, description="Coordinates of the element in the document", repr=False
    )
    level: int | None = Field(None, description="Level of the header")
    source: str | None = Field(None, description="Source of the element", repr=False)
    type: str | None = Field("text", description="Type of the element", repr=False)
    original: Any | None = Field(
        None, exclude=True, description="Original object from which the segment was extracted", repr=False
    )

    def text_cleaned(self):
        return self.text.replace(" | ", " ").replace("---", "").strip()

    def __repr_str__(self, join_str: str) -> str:
        return join_str.join(
            repr(v)
            if a is None
            else (
                f'{a}="{v[:100]}...{v[-100:]}"'.replace("\n", "")
                if isinstance(v, str) and len(v) > 200
                else f"{a}={v!r}"
            )
            for a, v in self.__repr_args__()
            if v and a not in {"INCLUDE_METADATA_KEYS"}
        )


class TableSegment(TextSegment):
    footer: str | None = Field(None, description="Footer of the table or figure, to explain variable acronyms.")
    html: str | None = Field(None, description="Content as HTML structured", repr=False)
    image: str | None = Field(None, description="URL/filepath of the element's image", repr=False)
    probability: float | None = Field(None, description="Probability or confidence of the segment's extraction")
    type: str | None = Field("table", description="Type of the element", repr=False)


class FigureSegment(TableSegment):
    type: str | None = Field("figure", description="Type of the element", repr=False)
