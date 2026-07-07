import pytest

from extralit_server.index import get_index_engine
from extralit_server.index.lancedb_engine import LanceIndexEngine

pytestmark = pytest.mark.asyncio


async def test_get_index_engine_yields_lance_engine(monkeypatch, tmp_path):
    monkeypatch.setattr("extralit_server.settings.settings.lancedb_uri", str(tmp_path / "lance"))
    seen = None
    async for engine in get_index_engine():
        seen = engine
    assert isinstance(seen, LanceIndexEngine)
