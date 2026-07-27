import pytest

from extralit_server.models import Field
from extralit_server.search_engine.commons import es_mapping_for_field


def _field(dtype: str) -> Field:
    # `FieldFactory.build(...)` is not usable synchronously here: `AsyncSQLAlchemyModelFactory`
    # overrides `_generate` (shared by both the create and build strategies) to be async, so
    # `.build()` returns an unawaited coroutine rather than a `Field`. This test needs no DB
    # round trip, so construct the model directly instead.
    return Field(name="col", settings={"type": "column", "dtype": dtype, "nullable": True})


class TestColumnFieldMapping:
    @pytest.mark.parametrize(
        ("dtype", "expected"),
        [
            ("int64", "long"),
            ("int32", "long"),
            ("float64", "double"),
            ("float32", "double"),
            ("bool", "boolean"),
            ("datetime64[ns]", "date_nanos"),
        ],
    )
    def test_numeric_and_temporal_dtypes_map_to_typed_es_fields(self, dtype, expected):
        mapping = es_mapping_for_field(_field(dtype))
        assert next(iter(mapping.values()))["type"] == expected

    def test_string_dtypes_map_to_text_with_a_keyword_subfield(self):
        mapping = es_mapping_for_field(_field("string"))
        es_field = next(iter(mapping.values()))
        assert es_field["type"] == "text"
        # A keyword sub-field is what makes terms filters and sorting on a column work.
        assert es_field["fields"]["keyword"]["type"] == "keyword"

    def test_an_unrecognized_dtype_falls_back_to_text(self):
        mapping = es_mapping_for_field(_field("some_extension_dtype"))
        assert next(iter(mapping.values()))["type"] == "text"

    def test_the_mapping_is_keyed_under_the_record_field_namespace(self):
        mapping = es_mapping_for_field(_field("string"))
        assert list(mapping.keys()) == ["fields.col"]
