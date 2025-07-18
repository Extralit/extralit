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
from uuid import uuid4
import factory

from argilla_server.models.database import ImportHistory
from tests.factories import UserFactory, WorkspaceFactory, BaseFactory


class ImportHistoryFactory(BaseFactory):
    class Meta:
        model = ImportHistory

    id = factory.LazyFunction(uuid4)
    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    bib_filename = factory.Sequence(lambda n: f"library-{n}.bib")
    document_info = {"reference_keys": ["ref1", "ref2", "ref3"]}
    import_summary = {"total": 3, "added": 2, "updated": 1, "skipped": 0, "failed": 0}


@pytest.mark.asyncio
class TestImportHistory:
    async def test_create_import_history(self):
        """Test that an ImportHistory record can be created with all required fields."""
        workspace = await WorkspaceFactory.create()
        user = await UserFactory.create()

        import_history = await ImportHistoryFactory.create(
            workspace=workspace,
            user=user,
            bib_filename="test-library.bib",
            document_info={"reference_keys": ["ref1", "ref2"]},
            import_summary={"total": 2, "added": 2, "updated": 0, "skipped": 0, "failed": 0},
        )

        assert import_history.workspace_id == workspace.id
        assert import_history.user_id == user.id
        assert import_history.bib_filename == "test-library.bib"
        assert import_history.document_info == {"reference_keys": ["ref1", "ref2"]}
        assert import_history.import_summary == {"total": 2, "added": 2, "updated": 0, "skipped": 0, "failed": 0}
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

    async def test_import_history_json_fields(self):
        """Test that the JSON fields in ImportHistory can store complex data structures."""
        document_info = {
            "reference_keys": ["ref1", "ref2", "ref3"],
            "metadata": {
                "ref1": {
                    "title": "Paper 1",
                    "authors": ["Author A", "Author B"],
                    "year": 2025,
                    "venue": "Journal of Testing",
                },
                "ref2": {"title": "Paper 2", "authors": ["Author C"], "year": 2024, "venue": "Conference on Testing"},
            },
        }

        import_summary = {
            "total": 3,
            "added": 1,
            "updated": 1,
            "skipped": 1,
            "failed": 0,
            "details": {"ref1": "added", "ref2": "updated", "ref3": "skipped"},
        }

        import_history = await ImportHistoryFactory.create(document_info=document_info, import_summary=import_summary)

        assert import_history.document_info == document_info
        assert import_history.import_summary == import_summary
        assert import_history.document_info["metadata"]["ref1"]["title"] == "Paper 1"
        assert import_history.import_summary["details"]["ref2"] == "updated"
