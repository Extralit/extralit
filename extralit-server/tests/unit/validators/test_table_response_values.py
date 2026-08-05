"""The additive table-value contract (spec §3.4): a bare dict is 1 row, `list[dict]` is N rows.

Restored from the deleted `validators/v2/values.py::V2ResponseValueValidator._validate_table`
(added by `046a3069f`, dropped with `tests/unit/validators/v2/` in the v2->v1 fold). The fold
ported the *read* half of §3.4 — `contexts/projection.py::table_arrays` still normalizes
`json_type(value) = 'ARRAY'` into fan-out rows — but not the write half, leaving multi-row
table values unrepresentable through the API even though the grid exists to display them.
"""

import pytest

from extralit_server.api.schemas.v1.questions import TableQuestionSettings
from extralit_server.api.schemas.v1.responses import (
    RankingQuestionResponseValueItem,
    ResponseValueCreate,
    SpanQuestionResponseValueItem,
)
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.response_values import (
    RankingQuestionResponseValueValidator,
    SpanQuestionResponseValueValidator,
    TableQuestionResponseValueValidator,
)

SETTINGS = TableQuestionSettings(type=QuestionType.table, columns=["a", "b"])


def _validate(value) -> None:
    TableQuestionResponseValueValidator(value).validate_for(SETTINGS)


def test_a_bare_dict_is_accepted_as_the_one_row_case():
    _validate({"a": 1, "b": "x"})


def test_a_list_of_row_dicts_is_accepted():
    _validate([{"a": 1}, {"a": 2, "b": "x"}])


def test_an_empty_list_is_accepted():
    # A table question the annotator cleared is legitimately zero rows, not a malformed value.
    _validate([])


def test_a_non_dict_row_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="dict of values per row"):
        _validate([{"a": 1}, 5])


def test_a_scalar_value_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="dict of values per row"):
        _validate("not-a-table")


class TestBlindUnionFallthrough:
    """Widening the table member made `ResponseValueTypes` able to match any list of objects.

    `ResponseValueTypes` is parsed before the question type is known, so a span or ranking
    item that fails its own strict model is no longer a parse error — it matches the table
    member and reaches the span/ranking validator as a plain dict. Those validators read
    `.start`/`.label`/`.rank` off their items, so without an explicit guard the request turns
    into a 500 instead of the 422 it used to be (caught by the pre-existing
    `test_create_record_response_for_span_question_with_*` cases).
    """

    def test_a_malformed_span_item_parses_as_a_table_row(self):
        # Documents the fallthrough itself, so the guards below have a stated reason to exist.
        parsed = ResponseValueCreate(value=[{"label": "a", "start": 3, "end": 2}])
        assert [type(item) for item in parsed.value] == [dict]

    def test_the_span_validator_rejects_a_fallen_through_dict(self):
        with pytest.raises(UnprocessableEntityError, match="list of span items"):
            SpanQuestionResponseValueValidator([{"label": "a", "start": 3, "end": 2}])._validate_value_type()

    def test_the_ranking_validator_rejects_a_fallen_through_dict(self):
        with pytest.raises(UnprocessableEntityError, match="list of ranking items"):
            RankingQuestionResponseValueValidator([{"rank": 1}])._validate_value_type()

    def test_well_formed_span_and_ranking_values_still_match_their_own_models(self):
        span = ResponseValueCreate(value=[{"label": "a", "start": 0, "end": 1}])
        ranking = ResponseValueCreate(value=[{"value": "a", "rank": 1}])
        assert [type(i) for i in span.value] == [SpanQuestionResponseValueItem]
        assert [type(i) for i in ranking.value] == [RankingQuestionResponseValueItem]
