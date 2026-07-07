import os
from pathlib import Path

from extralit_server.settings import Settings


def test_lancedb_uri_defaults_under_home_path():
    s = Settings(home_path="/tmp/extralit-home", lancedb_uri=None)
    assert s.lancedb_uri == os.path.join("/tmp/extralit-home", "lance")


def test_lancedb_uri_explicit_value_is_respected():
    s = Settings(home_path="/tmp/extralit-home", lancedb_uri="s3://bucket/lance")
    assert s.lancedb_uri == "s3://bucket/lance"


def test_lancedb_uri_reads_env_prefix(monkeypatch):
    monkeypatch.setenv("EXTRALIT_LANCEDB_URI", "/data/custom-lance")
    s = Settings(home_path="/tmp/extralit-home")
    assert s.lancedb_uri == "/data/custom-lance"
    assert Path("/data/custom-lance").name == "custom-lance"
