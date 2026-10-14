import json

from typer.testing import CliRunner

from extralit_server.cli import app

runner = CliRunner()


def test_openapi_dump_writes_v1_schema(tmp_path):
    output = tmp_path / "openapi.json"

    result = runner.invoke(app, ["openapi-dump", "--output", str(output)])

    assert result.exit_code == 0
    schema = json.loads(output.read_text())
    assert schema["info"]["title"] == "Extralit v1"
    assert "/datasets" in schema["paths"]
    assert "/me/datasets" in schema["paths"]


def test_openapi_dump_pins_the_contract_version(tmp_path, monkeypatch):
    monkeypatch.setattr("extralit_server.api.routes.api_v1.version", "9.9.9")
    # openapi() memoises into openapi_schema, so the cache must be dropped for the bump to apply.
    monkeypatch.setattr("extralit_server.api.routes.api_v1.openapi_schema", None)
    output = tmp_path / "openapi.json"

    assert runner.invoke(app, ["openapi-dump", "--output", str(output)]).exit_code == 0

    assert json.loads(output.read_text())["info"]["version"] == "v1"


def test_openapi_dump_is_deterministic(tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"

    assert runner.invoke(app, ["openapi-dump", "--output", str(first)]).exit_code == 0
    assert runner.invoke(app, ["openapi-dump", "--output", str(second)]).exit_code == 0

    assert first.read_bytes() == second.read_bytes()


def test_openapi_dump_prints_to_stdout_without_output():
    result = runner.invoke(app, ["openapi-dump"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["info"]["title"] == "Extralit v1"
