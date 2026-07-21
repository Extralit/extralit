import pytest

from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.v2.values import V2ResponseValueValidator, V2SuggestionValidator

LABEL_SETTINGS = {
    "type": "label_selection",
    "options": [{"value": "yes", "text": "Yes"}, {"value": "no", "text": "No"}],
    "strict": True,
}
TABLE_SETTINGS = {"type": "table"}


def test_text_value_must_be_str():
    V2ResponseValueValidator.validate("ok", type=QuestionType.text, settings={"type": "text"}, columns=["c"])
    with pytest.raises(UnprocessableEntityError):
        V2ResponseValueValidator.validate(5, type=QuestionType.text, settings={"type": "text"}, columns=["c"])


def test_label_must_be_in_options():
    V2ResponseValueValidator.validate("yes", type=QuestionType.label_selection, settings=LABEL_SETTINGS, columns=["c"])
    with pytest.raises(UnprocessableEntityError):
        V2ResponseValueValidator.validate(
            "maybe", type=QuestionType.label_selection, settings=LABEL_SETTINGS, columns=["c"]
        )


def test_table_value_keys_must_be_subset_of_columns():
    V2ResponseValueValidator.validate({"a": 1}, type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"])
    with pytest.raises(UnprocessableEntityError, match="not bound"):
        V2ResponseValueValidator.validate(
            {"z": 1}, type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"]
        )


def test_span_value_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="span"):
        V2ResponseValueValidator.validate([], type=QuestionType.span, settings={"type": "span"}, columns=["c"])


def test_unknown_question_type_fails_closed():
    # Guards against a future QuestionType member being wired through without a branch in
    # V2ResponseValueValidator.validate — the dispatch must reject, not silently accept.
    with pytest.raises(UnprocessableEntityError, match="unknown question type"):
        V2ResponseValueValidator.validate("x", type="bogus_type", settings={}, columns=["c"])


MULTI_LABEL_SETTINGS = {
    "type": "multi_label_selection",
    "options": [{"value": "yes", "text": "Yes"}],
}


def test_suggestion_score_length_must_match_list_value():
    V2SuggestionValidator.validate(
        ["yes"], [0.9], type=QuestionType.multi_label_selection, settings=MULTI_LABEL_SETTINGS, columns=["c"]
    )
    with pytest.raises(UnprocessableEntityError):
        V2SuggestionValidator.validate(
            ["yes"], [0.9, 0.1], type=QuestionType.multi_label_selection, settings=MULTI_LABEL_SETTINGS, columns=["c"]
        )


def test_table_value_accepts_list_of_row_dicts():
    V2ResponseValueValidator.validate(
        [{"a": 1}, {"a": 2, "b": "x"}], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"]
    )


def test_table_value_accepts_empty_list():
    V2ResponseValueValidator.validate([], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a"])


def test_table_value_list_rejects_unbound_keys_in_any_row():
    with pytest.raises(UnprocessableEntityError, match="not bound"):
        V2ResponseValueValidator.validate(
            [{"a": 1}, {"z": 2}], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a", "b"]
        )


def test_table_value_list_rejects_non_dict_rows():
    with pytest.raises(UnprocessableEntityError, match="dict of values per row"):
        V2ResponseValueValidator.validate(
            [{"a": 1}, 5], type=QuestionType.table, settings=TABLE_SETTINGS, columns=["a"]
        )
