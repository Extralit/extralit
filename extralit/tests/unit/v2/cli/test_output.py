import json

import pytest
import typer

from extralit.v2._api._errors import V2APIError, ValidationError
from extralit.v2.cli._output import emit, fail, to_jsonable
from extralit.v2.models import SearchPage


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
