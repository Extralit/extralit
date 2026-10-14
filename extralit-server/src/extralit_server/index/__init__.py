"""LanceDB index engine — deliberately parked, not dead code.

Nothing in `src/` imports this package: its former callers (`contexts/v2/index_sync.py`
and `cli/index/`) were written against the deleted v2 models and went with them in the
v2->v1 fold. The engine itself is model-agnostic and is kept for **ENG-36**, which
registers `LanceIndexEngine` as a `SearchEngine` implementation so LanceDB can replace
Elasticsearch/OpenSearch. Do not remove in a dead-code sweep; do not build a second
search path on /api/v1 alongside it.

Note for ENG-36: the fold dropped `schema_version_id` from the persisted row layout
(`mapping.py`), and the only rebuild path (`drop_table` -> repopulate) was deleted with
`cli/index`. `ensure_table` only *adds* missing columns, so a table written by the old
layout still carries that field and will mismatch on upsert. Reconciling a pre-existing
table needs either a rebuild entry point or obsolete-column detection in `ensure_table`.
"""

from collections.abc import AsyncGenerator

from extralit_server.index.base import IndexEngine
from extralit_server.index.lancedb_engine import LanceIndexEngine


async def get_index_engine() -> AsyncGenerator[IndexEngine, None]:
    """FastAPI dependency: yield an index engine, closing it afterwards.

    Mirrors `search_engine.get_search_engine`. The engine is currently always
    LanceIndexEngine; a registry can be added if a second backend appears.
    """
    engine = await LanceIndexEngine.new_instance()
    try:
        yield engine
    finally:
        await engine.close()
