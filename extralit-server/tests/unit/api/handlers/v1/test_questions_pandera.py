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
from uuid import uuid4
import httpx

from extralit_server.utils.pandera_utils import serialize_pandera_schema
from tests.factories import UserFactory, DatasetFactory


class TestQuestionPanderaSchema:
    async def test_create_question_with_pandera_schema(self, async_client: httpx.AsyncClient, owner_auth_header):
        """Test creating a question with a Pandera schema."""
        # Create a user and dataset
        user = await UserFactory.create()
        dataset = await DatasetFactory.create(workspace_id=user.default_workspace_id)
        
        # Create a simple Pandera schema
        schema = pa.DataFrameSchema({
            "name": pa.Column(pa.String),
            "score": pa.Column(pa.Int, pa.Check.ge(0)),
        })
        serialized_schema = serialize_pandera_schema(schema)
        
        # Create a question with the schema
        question_data = {
            "name": "test_question",
            "title": "Test Question",
            "description": "A test question with Pandera schema",
            "required": True,
            "settings": {
                "type": "text",
                "use_markdown": False,
                "use_table": True,  # Use table for DataFrame validation
            },
            "pandera_schema": serialized_schema,
        }
        
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json=question_data
        )
        
        assert response.status_code == 201
        question = response.json()
        
        # Verify the question was created with the schema
        assert question["name"] == "test_question"
        assert question["title"] == "Test Question"
        assert question["required"] is True
        
        # The pandera_schema should be stored in metadata, not returned in the standard response
        # We'll need to implement a separate endpoint or modify the response to include it
        
    async def test_create_question_with_invalid_pandera_schema(self, async_client: httpx.AsyncClient, owner_auth_header):
        """Test creating a question with an invalid Pandera schema."""
        # Create a user and dataset
        user = await UserFactory.create()
        dataset = await DatasetFactory.create(workspace_id=user.default_workspace_id)
        
        # Create question with invalid schema
        question_data = {
            "name": "test_question",
            "title": "Test Question",
            "description": "A test question with invalid schema",
            "required": True,
            "settings": {
                "type": "text",
            },
            "pandera_schema": {"invalid": "schema"},  # Invalid schema
        }
        
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json=question_data
        )
        
        assert response.status_code == 422
        assert "Invalid Pandera schema format" in response.text
        
    async def test_update_question_with_pandera_schema(self, async_client: httpx.AsyncClient, owner_auth_header):
        """Test updating a question to add a Pandera schema."""
        # Create a user and dataset
        user = await UserFactory.create()
        dataset = await DatasetFactory.create(workspace_id=user.default_workspace_id)
        
        # Create a question without schema first
        question_data = {
            "name": "test_question",
            "title": "Test Question",
            "settings": {
                "type": "label_selection",
                "options": [
                    {"value": "option1", "text": "Option 1"},
                    {"value": "option2", "text": "Option 2"},
                ],
                "strict": True
            },
        }
        
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json=question_data
        )
        
        assert response.status_code == 201
        question_id = response.json()["id"]
        
        # Create a series schema for label validation
        schema = pa.SeriesSchema(pa.String, name="selected_option")
        serialized_schema = serialize_pandera_schema(schema)
        
        # Update the question with a Pandera schema
        update_data = {
            "pandera_schema": serialized_schema,
        }
        
        response = await async_client.patch(
            f"/api/v1/questions/{question_id}",
            headers=owner_auth_header,
            json=update_data
        )
        
        assert response.status_code == 200
        updated_question = response.json()
        
        # The schema should be stored but the API needs to be enhanced to return it