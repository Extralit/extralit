import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import click
import pytest
from typer.testing import CliRunner

import extralit.v2.cli._context as context_mod
from extralit.v2._api._errors import ValidationError
from extralit.v2.cli.schemas import app
from extralit.v2.models import Schema

# click >= 8.2 separates stderr by default; 8.1 (Python 3.9) requires mix_stderr=False.
runner = (
    CliRunner() if tuple(int(x) for x in click.__version__.split(".")[:2]) >= (8, 2) else CliRunner(mix_stderr=False)
)
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _schema(name="trials"):
    return Schema.model_validate(
        {
            "id": str(uuid.uuid4()),
            "name": name,
            "status": "draft",
            "current_version_id": None,
            "settings": {},
            "workspace_id": WS,
            "inserted_at": NOW,
            "updated_at": NOW,
        }
    )


class FakeClient(SimpleNamespace):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient(schemas=SimpleNamespace(list=lambda workspace_id: [_schema()]))
    monkeypatch.setattr(context_mod, "get_client", lambda: client)
    # schemas.py imports get_client at call time via the module attribute:
    import extralit.v2.cli.schemas as schemas_mod

    monkeypatch.setattr(schemas_mod, "get_client", lambda: client)
    return client


def test_list_emits_json(fake_client):
    result = runner.invoke(app, ["list", "--workspace-id", WS, "--json"])
    assert result.exit_code == 0
    items = json.loads(result.stdout)
    assert items[0]["name"] == "trials"


def test_validation_error_exits_3(fake_client):
    def boom(workspace_id):
        raise ValidationError(422, "bad")

    fake_client.schemas.list = boom
    result = runner.invoke(app, ["list", "--workspace-id", WS, "--json"])
    assert result.exit_code == 3
    assert json.loads(result.stderr)["error"]["type"] == "ValidationError"


def test_top_level_registration():
    from extralit.cli.app import app as root_app

    names = [t.name for t in root_app.registered_groups]
    for verb in ("schemas", "records", "questions", "suggestions", "projection", "references"):
        assert verb in names, f"{verb} not registered at top level"
    assert names.count("schemas") == 1, "v1 schemas subcommand must be unregistered"
