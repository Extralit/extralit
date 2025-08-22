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
