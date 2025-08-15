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

from uuid import uuid4

import factory
import pytest

from extralit_server.models.database import ImportHistory
from tests.factories import BaseFactory, UserFactory, WorkspaceFactory


class ImportHistoryFactory(BaseFactory):
    class Meta:
        model = ImportHistory

    id = factory.LazyFunction(uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f"library-{n}.bib")
    data = {
        "documents": {
            "ref1": {
                "document_create": {
                    "reference": "ref1",
                    "pmid": None,
                    "doi": None,
                    "file_name": "paper1.pdf",
                    "url": None,
                },
                "title": "Test Paper 1",
                "authors": ["Author A"],
                "year": 2025,
                "venue": "Test Journal",
                "associated_files": ["paper1.pdf"],
                "status": "add",
                "validation_errors": [],
            }
        },
        "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
    }


@pytest.mark.asyncio
class TestImportHistory:
    async def test_create_import_history(self):
        """Test that an ImportHistory record can be created with all required fields."""
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()

        metadata = {
            "documents": {
                "ref1": {
                    "document_create": {
                        "reference": "ref1",
                        "pmid": None,
                        "doi": None,
                        "file_name": "paper1.pdf",
                        "url": None,
                    },
                    "title": "Test Paper 1",
                    "authors": ["Author A"],
                    "year": 2025,
                    "venue": "Test Journal",
                    "associated_files": ["paper1.pdf"],
                    "status": "add",
                    "validation_errors": [],
                }
            },
            "summary": {"total_documents": 1, "add_count": 1, "update_count": 0, "skip_count": 0, "failed_count": 0},
        }

        import_history = await ImportHistoryFactory.create(
            workspace=workspace,
            user=user,
            filename="test-library.bib",
            data=metadata,
        )

        assert import_history.workspace_id == workspace.id
        assert import_history.user_id == user.id
        assert import_history.filename == "test-library.bib"
        assert import_history.data == metadata
        assert import_history.inserted_at is not None

    async def test_import_history_relationships(self):
        """Test that the ImportHistory relationships to Workspace and User are properly set up."""
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()

        import_history = await ImportHistoryFactory.create(workspace=workspace, user=user)

        assert import_history.workspace.id == workspace.id
        assert import_history.workspace.name == workspace.name
        assert import_history.user.id == user.id
        assert import_history.user.username == user.username

    async def test_import_history_data_field(self):
        """Test that the data field in ImportHistory can store ImportAnalysisResponse data structures."""
        data = {
            "documents": {
                "ref1": {
                    "document_create": {
                        "reference": "ref1",
                        "pmid": "12345",
                        "doi": "10.1234/test",
                        "file_name": "paper1.pdf",
                        "url": None,
                    },
                    "title": "Paper 1",
                    "authors": ["Author A", "Author B"],
                    "year": 2025,
                    "venue": "Journal of Testing",
                    "associated_files": ["paper1.pdf"],
                    "status": "add",
                    "validation_errors": [],
                },
                "ref2": {
                    "document_create": {
                        "reference": "ref2",
                        "pmid": None,
                        "doi": None,
                        "file_name": "paper2.pdf",
                        "url": None,
                    },
                    "title": "Paper 2",
                    "authors": ["Author C"],
                    "year": 2024,
                    "venue": "Conference on Testing",
                    "associated_files": ["paper2.pdf"],
                    "status": "update",
                    "validation_errors": [],
                },
                "ref3": {
                    "document_create": {
                        "reference": "ref3",
                        "pmid": None,
                        "doi": None,
                        "file_name": "paper3.pdf",
                        "url": None,
                    },
                    "title": "Paper 3",
                    "authors": ["Author D"],
                    "year": 2023,
                    "venue": "Workshop Proceedings",
                    "associated_files": [],
                    "status": "skip",
                    "validation_errors": ["Missing PDF file"],
                },
            },
            "summary": {"total_documents": 3, "add_count": 1, "update_count": 1, "skip_count": 1, "failed_count": 0},
        }

        import_history = await ImportHistoryFactory.create(data=data)

        assert import_history.data == data
        assert import_history.data["documents"]["ref1"]["title"] == "Paper 1"
        assert import_history.data["documents"]["ref2"]["status"] == "update"
        assert import_history.data["summary"]["total_documents"] == 3
        assert import_history.data["summary"]["add_count"] == 1
