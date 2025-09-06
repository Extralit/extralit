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
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.questions import QuestionCreate, QuestionUpdate
from extralit_server.contexts import questions
from extralit_server.utils.pandera_utils import serialize_pandera_schema
from tests.factories import DatasetFactory


class TestQuestionPanderaSchemaIntegration:
    async def test_create_and_retrieve_question_with_pandera_schema(self, db: AsyncSession):
        """Test creating and retrieving a question with a Pandera schema."""
        # Create a dataset
        dataset = await DatasetFactory.create()
        
        # Create a simple Pandera schema
        schema = pa.DataFrameSchema({
            "name": pa.Column(pa.String),
            "score": pa.Column(pa.Int, pa.Check.ge(0)),
        })
        serialized_schema = serialize_pandera_schema(schema)
        
        # Create a question with the schema
        question_create = QuestionCreate(
            name="test_question",
            title="Test Question",
            description="A test question with Pandera schema",
            required=True,
            settings={
                "type": "text",
                "use_markdown": False,
                "use_table": True,
            },
            pandera_schema=serialized_schema,
        )
        
        # Create the question
        question = await questions.create_question(db, dataset, question_create)
        
        # Verify the question was created
        assert question.name == "test_question"
        assert question.title == "Test Question"
        assert question.required is True
        
        # Verify the Pandera schema was stored in metadata
        assert question.metadata_ is not None
        assert "pandera_schema" in question.metadata_
        assert question.metadata_["pandera_schema"] == serialized_schema
        
        # Verify the property accessor works
        assert question.pandera_schema == serialized_schema
        
    async def test_update_question_with_pandera_schema(self, db: AsyncSession):
        """Test updating a question to add/modify Pandera schema."""
        # Create a dataset and basic question
        dataset = await DatasetFactory.create()
        
        question_create = QuestionCreate(
            name="test_question",
            title="Test Question",
            settings={"type": "label_selection", "options": [{"value": "opt1", "text": "Option 1"}], "strict": True},
        )
        
        question = await questions.create_question(db, dataset, question_create)
        
        # Verify no schema initially
        assert question.pandera_schema is None
        
        # Create a series schema for label validation
        schema = pa.SeriesSchema(pa.String, name="selected_option")
        serialized_schema = serialize_pandera_schema(schema)
        
        # Update the question with a Pandera schema
        question_update = QuestionUpdate(pandera_schema=serialized_schema)
        
        updated_question = await questions.update_question(db, question, question_update)
        
        # Verify the schema was added
        assert updated_question.pandera_schema == serialized_schema
        assert updated_question.metadata_["pandera_schema"] == serialized_schema
        
        # Update to remove the schema
        question_update_remove = QuestionUpdate(pandera_schema=None)
        
        updated_question = await questions.update_question(db, updated_question, question_update_remove)
        
        # Verify the schema was removed
        assert updated_question.pandera_schema is None
        # Metadata might still exist but without pandera_schema key
        if updated_question.metadata_:
            assert "pandera_schema" not in updated_question.metadata_
            
    async def test_create_question_with_invalid_pandera_schema(self, db: AsyncSession):
        """Test that creating a question with invalid Pandera schema fails validation."""
        dataset = await DatasetFactory.create()
        
        # Create question with invalid schema
        question_create = QuestionCreate(
            name="test_question",
            title="Test Question",
            settings={"type": "text"},
            pandera_schema={"invalid": "schema"},  # Invalid schema
        )
        
        # This should raise a validation error
        with pytest.raises(ValueError, match="Invalid Pandera schema format"):
            await questions.create_question(db, dataset, question_create)