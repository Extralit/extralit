from collections.abc import AsyncGenerator

from extralit_server.index.base import IndexEngine
from extralit_server.index.lancedb_engine import LanceIndexEngine


async def get_index_engine() -> AsyncGenerator[IndexEngine, None]:
    """FastAPI dependency: yield a v2 index engine, closing it afterwards.

    Mirrors `search_engine.get_search_engine`. The engine is currently always
    LanceIndexEngine; a registry can be added if a second backend appears.
    """
    engine = await LanceIndexEngine.new_instance()
    try:
        yield engine
    finally:
        await engine.close()
