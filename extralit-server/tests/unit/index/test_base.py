import inspect
from uuid import uuid4

from extralit_server.index.base import IndexEngine, IndexFilter, IndexSearchHit, IndexSearchResult


def test_index_engine_is_abstract():
    import pytest

    with pytest.raises(TypeError):
        IndexEngine()  # abstract methods unimplemented


def test_required_async_methods_present():
    for name in ("close", "ensure_table", "drop_table", "upsert", "delete", "search", "table_names"):
        method = getattr(IndexEngine, name)
        assert inspect.iscoroutinefunction(method), f"{name} must be async"


def test_result_models_roundtrip():
    hit = IndexSearchHit(record_id=uuid4(), score=1.5)
    result = IndexSearchResult(hits=[hit], total=1)
    assert result.total == 1
    assert result.hits[0].score == 1.5


def test_index_filter_shape():
    f = IndexFilter(column="year", op="ge", value=2000)
    assert (f.column, f.op, f.value) == ("year", "ge", 2000)
