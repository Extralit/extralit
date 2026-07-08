import pytest

from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.v2.questions import QuestionBindingValidator

COLUMNS_CACHE = [
    {"name": "disease", "dtype": "str", "nullable": True, "review": None},
    {"name": "p_value", "dtype": "float64", "nullable": True, "review": None},
]


def test_non_table_binds_exactly_one_existing_column():
    QuestionBindingValidator.validate(
        type=QuestionType.label_selection, columns=["disease"], columns_cache=COLUMNS_CACHE
    )


def test_table_binds_one_or_more():
    QuestionBindingValidator.validate(
        type=QuestionType.table, columns=["disease", "p_value"], columns_cache=COLUMNS_CACHE
    )


def test_span_is_rejected():
    with pytest.raises(UnprocessableEntityError, match="span"):
        QuestionBindingValidator.validate(type=QuestionType.span, columns=["disease"], columns_cache=COLUMNS_CACHE)


def test_unknown_column_rejected():
    with pytest.raises(UnprocessableEntityError, match="unknown"):
        QuestionBindingValidator.validate(type=QuestionType.text, columns=["missing"], columns_cache=COLUMNS_CACHE)


def test_non_table_multiple_columns_rejected():
    with pytest.raises(UnprocessableEntityError, match="exactly one"):
        QuestionBindingValidator.validate(
            type=QuestionType.rating, columns=["disease", "p_value"], columns_cache=COLUMNS_CACHE
        )


def test_empty_binding_rejected():
    with pytest.raises(UnprocessableEntityError, match="at least one"):
        QuestionBindingValidator.validate(type=QuestionType.table, columns=[], columns_cache=COLUMNS_CACHE)
