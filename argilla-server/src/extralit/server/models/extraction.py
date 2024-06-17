from typing import Dict, Optional, List, Any, Union, Annotated, Any
from pydantic import BaseModel, Field, Extra

SchemaName = Annotated[str, Field(description="The schema name of the extraction.", examples=["schema_name"])]
FieldName = Annotated[str, Field(description="The name of the field.", examples=["field_name"])]
Value = Annotated[Any, Field(description="The value of the field.", examples=["value"])]

Data = List[Dict[FieldName, Value]]
Extractions = Dict[SchemaName, Data]


class ExtractionRequest(BaseModel):
    reference: str
    schema_name: str
    extractions: Extractions = Field(
        default_factory=dict,
        description="All of the extraction data for previously extracted as well as the extraction table of "
                    "`schema_name` to be extracted."
    )
    columns: list[str] | None = None
    headers: list[str] | None = None
    types: list[str] | None = None
    prompt: str | None = None


class FieldSchema(BaseModel):
    name: str
    type: str | None = None
    extDtype: str | None = None


class Schema(BaseModel):
    fields: List[FieldSchema]
    primaryKey: list[str] | None = None
    pandas_version: str | None


class ExtractionResponse(BaseModel):
    schema: Schema
    data: Data

    class Config:
        extra = Extra.ignore