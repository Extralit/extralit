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

"""Utilities for handling Pandera schema serialization and validation."""

import json
from typing import Any, Union

import pandera as pa
from pandera import DataFrameSchema, SeriesSchema


def serialize_pandera_schema(schema: Union[DataFrameSchema, SeriesSchema]) -> dict[str, Any]:
    """
    Serialize a Pandera schema to a JSON-compatible dictionary.
    
    Args:
        schema: A Pandera DataFrameSchema or SeriesSchema
        
    Returns:
        Dictionary representation of the schema that can be stored as JSON
    """
    if not isinstance(schema, (DataFrameSchema, SeriesSchema)):
        raise ValueError("Schema must be a Pandera DataFrameSchema or SeriesSchema")
    
    try:
        # Use Pandera's built-in to_json method if available (DataFrameSchema)
        if hasattr(schema, 'to_json'):
            return json.loads(schema.to_json())
        
        # Handle SeriesSchema manually
        if isinstance(schema, SeriesSchema):
            return {
                "schema_type": "SeriesSchema",
                "dtype": str(schema.dtype),
                "name": schema.name,
                "nullable": schema.nullable,
                "unique": schema.unique,
                "coerce": schema.coerce,
                "checks": [str(check) for check in (schema.checks or [])],
                "metadata": schema.metadata,
                "description": schema.description,
                "title": schema.title,
            }
        
        # Fallback to to_dict if to_json is not available
        return schema.to_dict()
    except Exception as e:
        raise ValueError(f"Failed to serialize Pandera schema: {str(e)}")


def deserialize_pandera_schema(schema_dict: dict[str, Any]) -> Union[DataFrameSchema, SeriesSchema]:
    """
    Deserialize a dictionary back into a Pandera schema.
    
    Args:
        schema_dict: Dictionary representation of a Pandera schema
        
    Returns:
        A Pandera DataFrameSchema or SeriesSchema instance
    """
    if not isinstance(schema_dict, dict):
        raise ValueError("Schema data must be a dictionary")
    
    try:
        # Check if it's a SeriesSchema
        if schema_dict.get("schema_type") == "SeriesSchema":
            return pa.SeriesSchema(
                dtype=schema_dict.get("dtype", pa.String),
                name=schema_dict.get("name"),
                nullable=schema_dict.get("nullable", True),
                unique=schema_dict.get("unique", False),
                coerce=schema_dict.get("coerce", False),
                # Note: checks and other complex attributes would need more sophisticated handling
            )
        
        # Try to determine DataFrameSchema type from the dictionary structure
        if 'columns' in schema_dict or 'index' in schema_dict:
            # This looks like a DataFrameSchema
            if hasattr(pa.DataFrameSchema, 'from_json'):
                return pa.DataFrameSchema.from_json(json.dumps(schema_dict))
            else:
                return pa.DataFrameSchema.from_dict(schema_dict)
        else:
            # Default to DataFrameSchema
            if hasattr(pa.DataFrameSchema, 'from_json'):
                return pa.DataFrameSchema.from_json(json.dumps(schema_dict))
            else:
                return pa.DataFrameSchema.from_dict(schema_dict)
    except Exception as e:
        raise ValueError(f"Failed to deserialize Pandera schema: {str(e)}")


def validate_pandera_schema_dict(schema_dict: dict[str, Any]) -> bool:
    """
    Validate that a dictionary can be successfully deserialized into a Pandera schema.
    
    Args:
        schema_dict: Dictionary representation of a Pandera schema
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check for required keys that indicate a valid schema
        if isinstance(schema_dict, dict):
            # For SeriesSchema, check for schema_type
            if schema_dict.get("schema_type") == "SeriesSchema":
                return "dtype" in schema_dict
            
            # For DataFrameSchema, check for columns or other valid structure
            if "columns" in schema_dict or "index" in schema_dict:
                return True
                
        return False
    except Exception:
        return False