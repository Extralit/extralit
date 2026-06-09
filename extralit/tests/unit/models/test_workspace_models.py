from datetime import datetime

from dateutil import tz

from extralit._models import WorkspaceModel


class TestWorkspaceModels:
    def test_create_workspace_with_isoformat_string(self):
        workspace = WorkspaceModel(
            name="workspace",
            inserted_at="2024-12-12T09:44:24.989000Z",
            updated_at="2024-12-12T09:44:24.989000Z",
        )

        expected_datetime = datetime(2024, 12, 12, 9, 44, 24, 989000, tzinfo=tz.tzutc())

        assert workspace.name == "workspace"

        assert workspace.inserted_at == expected_datetime
        assert workspace.updated_at == expected_datetime
