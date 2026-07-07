from uuid import uuid4

import pytest

from extralit_server.index.base import IndexFilter
from extralit_server.index.lancedb_engine import LanceIndexEngine
from extralit_server.index.mapping import record_to_row

pytestmark = pytest.mark.asyncio

COLUMNS = [
    {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
    {"name": "year", "dtype": "int64", "nullable": True, "review": None},
]


class _Rec:
    def __init__(self, title, year, reference="pmid:1", external_id=None):
        from extralit_server.enums import V2RecordStatus

        self.id = uuid4()
        self.reference = reference
        self.schema_version_id = uuid4()
        self.status = V2RecordStatus.pending
        self.external_id = external_id
        self.fields = {"title": title, "year": year}


@pytest.fixture
async def engine(tmp_path):
    eng = LanceIndexEngine(uri=str(tmp_path / "lance"))
    yield eng
    await eng.close()


async def test_ensure_upsert_and_fts_search(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("Deep Learning Foundations", 2016), _Rec("Shallow Ponds", 1999)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, text="Deep Learning", offset=0, limit=10)
    assert result.total >= 1
    assert recs[0].id in [h.record_id for h in result.hits]


async def test_scalar_filter_without_text(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("A", 2016), _Rec("B", 1999)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="ge", value=2000)], limit=10)
    ids = [h.record_id for h in result.hits]
    assert recs[0].id in ids and recs[1].id not in ids


async def test_upsert_updates_in_place(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    rec = _Rec("Original", 2000)
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)
    rec.fields["title"] = "Rewritten"
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="eq", value=2000)], limit=10)
    assert len([h for h in result.hits if h.record_id == rec.id]) == 1


async def test_delete_removes_rows(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    rec = _Rec("Doomed", 2010)
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)
    await engine.delete(sid, [rec.id])

    result = await engine.search(sid, filters=[IndexFilter(column="year", op="eq", value=2010)], limit=10)
    assert rec.id not in [h.record_id for h in result.hits]


async def test_ensure_table_evolves_to_superset(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    evolved = [*COLUMNS, {"name": "doi", "dtype": "string[pyarrow]", "nullable": True, "review": None}]
    await engine.ensure_table(sid, evolved)  # idempotent + adds `doi`

    # Confirm the new column is present in the live schema.
    from extralit_server.index.mapping import table_name_for

    db = engine._db
    table = await db.open_table(table_name_for(sid))
    live_names = (await table.schema()).names
    assert "doi" in live_names

    # Confirm the evolved column is usable in a filter.
    from extralit_server.index.base import IndexFilter

    result = await engine.search(sid, filters=[IndexFilter(column="doi", op="eq", value=None)], limit=10)
    assert isinstance(result.total, int)  # no exception; doi is a valid filter column


async def test_fts_total_counts_matches_not_table_rows(engine):
    # `count_rows` cannot evaluate the FTS match, so `total` must come from the match
    # set: 2 of 3 rows match "Deep"; the page respects `limit` but `total` reports 2.
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("Deep Learning Foundations", 2016), _Rec("Shallow Ponds", 1999), _Rec("Deep Sea Biology", 2005)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    result = await engine.search(sid, text="Deep", offset=0, limit=1)
    assert len(result.hits) == 1
    assert result.total == 2


async def test_unknown_filter_column_raises(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("A", 2016)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    with pytest.raises(ValueError, match="disallowed filter column"):
        await engine.search(sid, filters=[IndexFilter(column="injected) OR (1=1", op="eq", value=1)], limit=10)


async def test_filter_op_in_rejects_scalar_string(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    recs = [_Rec("A", 2016)]
    await engine.upsert(sid, [record_to_row(r, COLUMNS) for r in recs], COLUMNS)

    with pytest.raises(TypeError, match="list/tuple"):
        await engine.search(sid, filters=[IndexFilter(column="year", op="in", value="2016")], limit=10)


async def test_filter_eq_none_matches_null_rows(engine):
    sid = uuid4()
    await engine.ensure_table(sid, COLUMNS)
    # external_id is a SYSTEM_FIELDS column; rows with external_id=None should match IS NULL
    rec = _Rec("A", 2016, external_id=None)
    await engine.upsert(sid, [record_to_row(rec, COLUMNS)], COLUMNS)

    result = await engine.search(sid, filters=[IndexFilter(column="external_id", op="eq", value=None)], limit=10)
    assert rec.id in [h.record_id for h in result.hits]


async def test_sql_type_covers_every_mapped_arrow_type():
    # Create-path (`arrow_schema_for`) and evolve-path (`add_columns` cast) must agree:
    # every Arrow type `arrow_type_for` can produce needs a SQL type entry, or an evolved
    # column (e.g. datetime) would silently become `string`.
    from extralit_server.index.lancedb_engine import _SQL_TYPE_BY_ARROW
    from extralit_server.index.mapping import _ARROW_BY_DTYPE

    for arrow_type in set(_ARROW_BY_DTYPE.values()):
        assert arrow_type in _SQL_TYPE_BY_ARROW, f"no SQL type for Arrow type {arrow_type}"
