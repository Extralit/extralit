"""The additive table-value contract (spec §3.4): a bare dict is 1 row, `list[dict]` is N rows.

Restored from the deleted `validators/v2/values.py::V2ResponseValueValidator._validate_table`
(added by `046a3069f`, dropped with `tests/unit/validators/v2/` in the v2->v1 fold). The fold
ported the *read* half of §3.4 — `contexts/projection.py::table_arrays` still normalizes
`json_type(value) = 'ARRAY'` into fan-out rows — but not the write half, leaving multi-row
table values unrepresentable through the API even though the grid exists to display them.
"""

import pytest

from extralit_server.api.schemas.v1.questions import TableQuestionSettings
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.response_values import TableQuestionResponseValueValidator

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
