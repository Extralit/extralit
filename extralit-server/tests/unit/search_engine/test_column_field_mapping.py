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

    @pytest.mark.parametrize(
        ("dtype", "expected"),
        [
            # pandas' extension dtypes -- what `str(Column.dtype)` yields for a column
            # declared `pd.Int64Dtype()` and friends (the ordinary way to get a nullable
            # numeric column). It survives to_json/from_json, so it is the spelling the
            # server actually stores. Before normalization every one of these fell through
            # to the text fallback, costing the column its numeric range queries and its
            # numeric sort order.
            ("Int64", "long"),
            ("Int32", "long"),
            ("Int8", "long"),
            ("Float64", "double"),
            ("Float32", "double"),
            # A timezone-aware datetime spells its zone into the dtype; the mapping must not
            # vary by zone, since `date_nanos` stores an instant.
            ("datetime64[ns, UTC]", "date_nanos"),
            ("datetime64[ns, America/Los_Angeles]", "date_nanos"),
        ],
    )
    def test_nullable_and_tz_aware_dtypes_map_like_their_plain_spellings(self, dtype, expected):
        mapping = es_mapping_for_field(_field(dtype))
        assert next(iter(mapping.values()))["type"] == expected

    def test_a_nullable_column_maps_identically_to_its_numpy_spelling(self):
        # The invariant behind the normalization: one logical type, one mapping. Otherwise a
        # range filter behaves differently depending on how the Pandera body declared it.
        assert es_mapping_for_field(_field("Int64")) == es_mapping_for_field(_field("int64"))
        assert es_mapping_for_field(_field("Float64")) == es_mapping_for_field(_field("float64"))

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
