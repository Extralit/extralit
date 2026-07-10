import json

from typer.testing import CliRunner

from extralit_server.cli import app

runner = CliRunner()


def test_openapi_dump_writes_v2_schema(tmp_path):
    output = tmp_path / "openapi.json"

    result = runner.invoke(app, ["openapi-dump", "--output", str(output)])

    assert result.exit_code == 0
    schema = json.loads(output.read_text())
    assert schema["info"]["title"] == "Extralit v2"
    assert "/schemas" in schema["paths"]
    assert "/projection/references/{reference}" in schema["paths"]


def test_openapi_dump_is_deterministic(tmp_path):
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"

    assert runner.invoke(app, ["openapi-dump", "--output", str(first)]).exit_code == 0
    assert runner.invoke(app, ["openapi-dump", "--output", str(second)]).exit_code == 0

    assert first.read_bytes() == second.read_bytes()


def test_openapi_dump_prints_to_stdout_without_output():
    result = runner.invoke(app, ["openapi-dump"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["info"]["title"] == "Extralit v2"
