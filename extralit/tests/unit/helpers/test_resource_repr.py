import uuid

import extralit as ex
from extralit._helpers._resource_repr import ResourceHTMLReprMixin


class TestResourceHTMLReprMixin:
    def test_represent_workspaces_as_html(self):
        client = ex.Extralit()
        workspaces = [
            ex.Workspace(name="workspace1", id=uuid.uuid4()),
            ex.Workspace(name="workspace2", id=uuid.uuid4()),
        ]

        assert (
            ResourceHTMLReprMixin()._represent_as_html(workspaces) == "<h3>Workspaces</h3>"
            "<table>"
            "<tr><th>name</th><th>id</th><th>updated_at</th></tr>"
            f"<tr><td>workspace1</td><td>{workspaces[0].id!s}</td><td>None</td></tr>"
            f"<tr><td>workspace2</td><td>{workspaces[1].id!s}</td><td>None</td></tr>"
            "</table>"
            ""
        )

        workspace = ex.Workspace(name="workspace1", id=uuid.uuid4())
        datasets = [
            ex.Dataset(name="dataset1", workspace=workspace, client=client),
            ex.Dataset(name="dataset2", workspace=workspace, client=client),
        ]

        for dataset in datasets:
            dataset.id = uuid.uuid4()

        assert (
            ResourceHTMLReprMixin()._represent_as_html(datasets) == "<h3>Datasets</h3>"
            "<table>"
            "<tr><th>name</th><th>id</th><th>workspace_id</th><th>updated_at</th></tr>"
            f"<tr><td>dataset1</td><td>{datasets[0].id!s}</td><td>{workspace.id!s}</td><td>None</td></tr>"
            f"<tr><td>dataset2</td><td>{datasets[1].id!s}</td><td>{workspace.id!s}</td><td>None</td></tr>"
            "</table>"
        )
