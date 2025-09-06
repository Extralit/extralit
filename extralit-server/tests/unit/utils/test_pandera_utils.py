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

import pytest
import pandera as pa
import json

from extralit_server.utils.pandera_utils import (
    serialize_pandera_schema,
    deserialize_pandera_schema,
    validate_pandera_schema_dict,
)


class TestPanderaUtils:
    def test_serialize_dataframe_schema(self):
        """Test serialization of DataFrameSchema."""
        schema = pa.DataFrameSchema({
            "name": pa.Column(pa.String),
            "age": pa.Column(pa.Int, pa.Check.ge(0)),
        })
        
        serialized = serialize_pandera_schema(schema)
        assert isinstance(serialized, dict)
        assert "columns" in serialized
        
    def test_serialize_series_schema(self):
        """Test serialization of SeriesSchema."""
        schema = pa.SeriesSchema(pa.String, name="name")
        
        serialized = serialize_pandera_schema(schema)
        assert isinstance(serialized, dict)
        
    def test_deserialize_dataframe_schema(self):
        """Test deserialization of DataFrameSchema."""
        original_schema = pa.DataFrameSchema({
            "name": pa.Column(pa.String),
            "age": pa.Column(pa.Int),
        })
        
        serialized = serialize_pandera_schema(original_schema)
        deserialized = deserialize_pandera_schema(serialized)
        
        assert isinstance(deserialized, pa.DataFrameSchema)
        
    def test_validate_schema_dict_valid(self):
        """Test validation of valid schema dictionary."""
        schema = pa.DataFrameSchema({
            "name": pa.Column(pa.String),
            "age": pa.Column(pa.Int),
        })
        
        serialized = serialize_pandera_schema(schema)
        assert validate_pandera_schema_dict(serialized) is True
        
    def test_validate_schema_dict_invalid(self):
        """Test validation of invalid schema dictionary."""
        invalid_schema = {"invalid": "schema"}
        assert validate_pandera_schema_dict(invalid_schema) is False
        
    def test_serialize_invalid_schema(self):
        """Test serialization with invalid schema type."""
        with pytest.raises(ValueError, match="Schema must be a Pandera"):
            serialize_pandera_schema("not a schema")
            
    def test_deserialize_invalid_dict(self):
        """Test deserialization with invalid dictionary."""
        with pytest.raises(ValueError, match="Schema data must be a dictionary"):
            deserialize_pandera_schema("not a dict")