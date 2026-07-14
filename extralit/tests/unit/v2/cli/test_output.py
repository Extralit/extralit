import json

import click
import pytest
import typer
from typer.testing import CliRunner

from extralit.v2._api._errors import V2APIError, ValidationError
from extralit.v2.cli._output import emit, fail, to_jsonable
from extralit.v2.models import SearchPage

# click >= 8.2 separates stderr by default; 8.1 (Python 3.9) requires mix_stderr=False.
_runner = (
    CliRunner() if tuple(int(x) for x in click.__version__.split(".")[:2]) >= (8, 2) else CliRunner(mix_stderr=False)
)


def test_to_jsonable_handles_models_lists_dicts():
    page = SearchPage(items=[], total=3)
    assert to_jsonable(page) == {"items": [], "total": 3}
    assert to_jsonable([page]) == [{"items": [], "total": 3}]
    assert to_jsonable({"a": 1}) == {"a": 1}


def test_emit_json_when_flag_set(capsys):
    emit({"a": 1}, json_flag=True)
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_emit_json_when_not_a_tty(capsys):
    emit({"a": 1}, json_flag=False)  # pytest capture is not a tty -> auto-JSON
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_fail_validation_exits_3_with_stderr_json(capsys):
    with pytest.raises(typer.Exit) as excinfo:
        fail(ValidationError(422, "bad value"))
    assert excinfo.value.exit_code == 3
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["status"] == 422 and err["error"]["type"] == "ValidationError"


def test_fail_api_error_exits_1(capsys):
    with pytest.raises(typer.Exit) as excinfo:
        fail(V2APIError(500, "kaboom"))
    assert excinfo.value.exit_code == 1
    assert json.loads(capsys.readouterr().err)["error"]["detail"] == "kaboom"


def test_handle_errors_routes_value_error_to_structured_fail(monkeypatch):
    """Malformed UUID must produce exit code 1 + structured stderr via handle_errors, not a traceback.

    get_client is monkeypatched so credentials resolution succeeds and the ValueError
    provably originates from UUID('not-a-uuid') inside upsert_records (after JSONL is read).
    """
    from types import SimpleNamespace

    import extralit.v2.cli.records as records_mod
    from extralit.v2.cli.records import app as records_app

    class _FakeClient(SimpleNamespace):
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(
        records_mod, "get_client", lambda: _FakeClient(records=SimpleNamespace(bulk_upsert=lambda *a, **k: []))
    )
    runner = _runner
    # Pass valid JSONL via stdin; the UUID is what's malformed
    result = runner.invoke(records_app, ["upsert", "not-a-uuid"], input='{"size": "10"}\n')
    assert result.exit_code == 1
    err = json.loads(result.stderr)
    assert err["error"]["type"] == "ValueError"
    assert "UUID" in err["error"]["detail"] or "hexadecimal" in err["error"]["detail"]


def test_handle_errors_routes_oserror_to_structured_fail():
    """Missing --file path must produce exit code 1 + structured stderr, not a traceback."""
    import uuid

    from extralit.v2.cli.records import app as records_app

    runner = _runner
    schema_id = str(uuid.uuid4())
    result = runner.invoke(records_app, ["upsert", schema_id, "--file", "/nonexistent/path/to/file.jsonl"])
    assert result.exit_code == 1
    err = json.loads(result.stderr)
    assert err["error"]["type"] in ("FileNotFoundError", "OSError")
