from typing import Optional

import pandera as pa
from pydantic.v1 import BaseModel, Field


class SchemaStructure(BaseModel):
    """
    A class representing the structure of a schema.

    Usage:
    ```python
    from pandera import DataFrameSchema
    from extralit._models._schema import SchemaStructure

    schema_structure = SchemaStructure(
        schemas=[
            DataFrameSchema(
                columns={
                    "name": pa.Column(pa.String),
                    "age": pa.Column(pa.Int)
                }
            )
        ]
    )
    ```
    """

    schemas: list[pa.DataFrameSchema] = Field(default_factory=list, description="A list of all the extraction schemas.")
    singleton_schema: Optional[pa.DataFrameSchema] = Field(
        None, repr=True, description="A singleton schema that exists in `schemas` list."
    )

    class Config:
        arbitrary_types_allowed = True
