from types import SimpleNamespace
from uuid import uuid4

import pyarrow as pa

from extralit_server.enums import V2RecordStatus
from extralit_server.index import mapping

COLUMNS = [
    {"name": "title", "dtype": "string[pyarrow]", "nullable": False, "review": None},
    {"name": "year", "dtype": "int64", "nullable": True, "review": None},
    {"name": "score", "dtype": "float64", "nullable": True, "review": None},
]


def test_table_name_is_hex_prefixed():
    sid = uuid4()
    assert mapping.table_name_for(sid) == f"schema_{sid.hex}"


def test_arrow_type_mapping_covers_pandera_dtypes():
    assert mapping.arrow_type_for("string[pyarrow]") == pa.large_string()
    assert mapping.arrow_type_for("int64") == pa.int64()
    assert mapping.arrow_type_for("float64") == pa.float64()
    assert mapping.arrow_type_for("bool") == pa.bool_()
    assert pa.types.is_timestamp(mapping.arrow_type_for("datetime64[ns]"))


def test_arrow_type_unknown_dtype_falls_back_to_string():
    assert mapping.arrow_type_for("category") == pa.large_string()


def test_arrow_schema_has_system_fields_and_typed_columns():
    schema = mapping.arrow_schema_for(COLUMNS)
    names = schema.names
    for sys_field in mapping.SYSTEM_FIELDS:
        assert sys_field in names
    assert schema.field("year").type == pa.int64()
    assert schema.field("text").type == pa.large_string()


def test_union_columns_dedupes_by_name_first_wins():
    v1 = [{"name": "a", "dtype": "int64", "nullable": True, "review": None}]
    v2 = [
        {"name": "a", "dtype": "int64", "nullable": True, "review": None},
        {"name": "b", "dtype": "string[pyarrow]", "nullable": True, "review": None},
    ]
    union = mapping.union_columns([v1, v2])
    assert [c["name"] for c in union] == ["a", "b"]


def test_concat_text_joins_string_columns_only():
    fields = {"title": "Deep Learning", "year": 2016, "score": 9.1}
    text = mapping.concat_text(fields, COLUMNS)
    assert "title: Deep Learning" in text
    assert "year" not in text  # non-string dtype excluded


def test_record_to_row_fills_missing_cells_with_none():
    rec = SimpleNamespace(
        id=uuid4(),
        reference="pmid:1",
        schema_version_id=uuid4(),
        status=V2RecordStatus.pending,
        external_id="x-1",
        fields={"title": "Deep Learning"},  # `year`/`score` absent
    )
    row = mapping.record_to_row(rec, COLUMNS)
    assert row["record_id"] == str(rec.id)
    assert row["schema_version_id"] == str(rec.schema_version_id)
    assert row["status"] == V2RecordStatus.pending.value
    assert row["title"] == "Deep Learning"
    assert row["year"] is None
    assert row["score"] is None
    assert row["text"] == "title: Deep Learning"
    # every arrow-schema field is present as a key
    assert set(row) == set(mapping.arrow_schema_for(COLUMNS).names)
