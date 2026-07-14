import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from extralit.v2.cli.records import _parse_filter, app
from extralit.v2.models import Record, SearchPage

runner = CliRunner()  # click >= 8.2: stderr is separated by default (mix_stderr was removed)
SCHEMA_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _record():
    return Record.model_validate(
        {
            "id": str(uuid.uuid4()),
            "schema_id": SCHEMA_ID,
            "schema_version_id": str(uuid.uuid4()),
            "reference": "10.1000/xyz",
            "external_id": None,
            "fields": {"size": "120"},
            "metadata": None,
            "status": "pending",
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
    calls = {}

    def upsert(schema_id, items, reference=None):
        calls["upsert"] = (schema_id, items, reference)
        return [_record()]

    def search(schema_id, text=None, filters=None, offset=0, limit=50):
        calls["search"] = (schema_id, text, filters, offset, limit)
        return SearchPage(items=[_record()], total=1)

    client = FakeClient(records=SimpleNamespace(bulk_upsert=upsert, search=search))
    import extralit.v2.cli.records as records_mod

    monkeypatch.setattr(records_mod, "get_client", lambda: client)
    return calls


def test_parse_filter_json_decodes_value():
    assert _parse_filter("age:ge:18") == ("age", "ge", 18)
    assert _parse_filter('label:in:["a","b"]') == ("label", "in", ["a", "b"])
    assert _parse_filter("country:eq:KE") == ("country", "eq", "KE")


def test_upsert_reads_jsonl_from_stdin(fake_client):
    lines = '{"size": "120"}\n{"size": "135"}\n'
    result = runner.invoke(app, ["upsert", SCHEMA_ID, "--reference", "10.1000/xyz"], input=lines)
    assert result.exit_code == 0, result.stderr
    _schema_id, items, reference = fake_client["upsert"]
    assert items == [{"size": "120"}, {"size": "135"}]
    assert reference == "10.1000/xyz"
    assert json.loads(result.stdout)[0]["fields"] == {"size": "120"}


def test_search_passes_filters(fake_client):
    result = runner.invoke(app, ["search", SCHEMA_ID, "--text", "tumor", "--filter", "age:ge:18", "--limit", "10"])
    assert result.exit_code == 0
    _, text, filters, _, limit = fake_client["search"]
    assert text == "tumor" and filters == [("age", "ge", 18)] and limit == 10
    assert json.loads(result.stdout)["total"] == 1
