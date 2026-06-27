import json

import pandera as pa
import pytest

from extralit_server.contexts.v2.schema_bodies import (
    SchemaValidationError,
    derive_columns_cache,
    validate_record_fields,
)


def _body() -> str:
    schema = pa.DataFrameSchema(
        columns={
            "name": pa.Column(pa.String, nullable=False),
            "age": pa.Column(pa.Int, nullable=True),
        }
    )
    return schema.to_json()


def test_derive_columns_cache_lists_columns_with_dtype_and_nullable():
    cache = derive_columns_cache(_body())
    by_name = {c["name"]: c for c in cache}
    assert set(by_name) == {"name", "age"}
    assert by_name["name"]["nullable"] is False
    assert by_name["age"]["nullable"] is True
    assert "int" in by_name["age"]["dtype"].lower()


def test_derive_columns_cache_defaults_review_to_none():
    # Pandera 0.32 drops per-Column.metadata through to_json/from_json, so the body alone
    # carries no review widget — `review` is None unless supplied via the side map.
    cache = derive_columns_cache(_body())
    assert all(c["review"] is None for c in cache)


def test_derive_columns_cache_merges_review_widgets_side_map():
    # The review widget is carried out-of-band (see spec §13) and merged per column name.
    cache = derive_columns_cache(_body(), review_widgets={"age": {"type": "rating"}})
    by_name = {c["name"]: c for c in cache}
    assert by_name["age"]["review"] == {"type": "rating"}
    assert by_name["name"]["review"] is None


def test_validate_record_fields_returns_native_json_types():
    coerced = validate_record_fields(_body(), {"name": "Ada", "age": 36})
    assert coerced["name"] == "Ada"
    assert coerced["age"] == 36
    # Must be native python types (not numpy scalars) and JSON-serializable for the
    # record.fields JSONB column in Phase 2.
    assert type(coerced["age"]) is int
    json.dumps(coerced)  # raises if numpy scalars / NaN leaked through


def test_validate_record_fields_converts_nulls_to_none():
    coerced = validate_record_fields(_body(), {"name": "Ada", "age": None})
    assert coerced["age"] is None
    json.dumps(coerced)


def test_validate_record_fields_raises_on_type_error():
    with pytest.raises(SchemaValidationError) as exc:
        validate_record_fields(_body(), {"name": "Ada", "age": "not-a-number"})
    assert isinstance(exc.value.errors, list)
    assert len(exc.value.errors) >= 1
