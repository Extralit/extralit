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
        description="All previously extracted data."
    )
    columns: Optional[List[str]] = None
    headers: Optional[List[str]] = None
    types: Optional[List[str]] = None
    prompt: Optional[str] = None


class FieldSchema(BaseModel):
    name: str
    type: Optional[str] = None
    extDtype: Optional[str] = None


class Schema(BaseModel):
    fields: List[FieldSchema]
    primaryKey: Optional[List[str]] = None
    pandas_version: Optional[str]


class ExtractionResponse(BaseModel):
    schema: Schema
    data: Data

    class Config:
        extra = Extra.ignore
