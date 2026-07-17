import json
import uuid
from types import SimpleNamespace

from typer.testing import CliRunner

from extralit.cli.app import app as root_app
from extralit.v2.models import ProjectionView

# Invoke through the mounted root app so the verb group name ("suggestions"/"projection")
# and its subcommand ("upsert"/"get") are both required — this matches real CLI usage.
# (Invoking a single-command Typer standalone promotes the command and drops its name,
# which is not how these verbs are actually invoked once mounted by add_v2_commands.)
runner = CliRunner()
RECORD_ID = str(uuid.uuid4())
Q_ID = str(uuid.uuid4())
WS = str(uuid.uuid4())


class FakeClient(SimpleNamespace):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


def test_suggestions_upsert_decodes_json_value(monkeypatch):
    calls = {}

    def upsert(record, question, value, score=None, agent=None, schema_id=None):
        calls["args"] = (record, question, value, score, agent, schema_id)
        return SimpleNamespace(model_dump=lambda mode: {"ok": True})

    client = FakeClient(suggestions=SimpleNamespace(upsert=upsert))
    import extralit.v2.cli.suggestions as mod

    monkeypatch.setattr(mod, "get_client", lambda: client)
    result = runner.invoke(
        root_app,
        [
            "suggestions",
            "upsert",
            RECORD_ID,
            "--question-id",
            Q_ID,
            "--value",
            '"120"',
            "--score",
            "0.9",
            "--agent",
            "claude",
        ],
    )
    assert result.exit_code == 0, result.output
    record, question, value, score, agent, _schema_id = calls["args"]
    assert (record, question, value, score, agent) == (RECORD_ID, Q_ID, "120", 0.9, "claude")


def test_suggestions_upsert_name_requires_schema_id(monkeypatch):
    import extralit.v2.cli.suggestions as mod

    monkeypatch.setattr(mod, "get_client", lambda: FakeClient(suggestions=SimpleNamespace()))
    result = runner.invoke(root_app, ["suggestions", "upsert", RECORD_ID, "--question", "size", "--value", '"x"'])
    assert result.exit_code == 2  # usage error: --question needs --schema-id


def test_projection_get(monkeypatch):
    view = ProjectionView(reference="10.1000/j.abc", records=[], total_records=0)
    client = FakeClient(projections=SimpleNamespace(get=lambda ws, ref: view))
    import extralit.v2.cli.projection as mod

    monkeypatch.setattr(mod, "get_client", lambda: client)
    result = runner.invoke(root_app, ["projection", "get", "10.1000/j.abc", "--workspace-id", WS])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["reference"] == "10.1000/j.abc"
