from pydantic import TypeAdapter

from extralit_server.api.schemas.v1.questions import QuestionSettings
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.response_values import (
    LabelSelectionQuestionResponseValueValidator,
    MultiLabelSelectionQuestionResponseValueValidator,
    RankingQuestionResponseValueValidator,
    RatingQuestionResponseValueValidator,
    TextQuestionResponseValueValidator,
)

DEFERRED_TYPES = {QuestionType.span}


def _parsed(settings: dict):
    # Reuse v1's discriminated QuestionSettings union so options/ranges are typed like v1.
    return TypeAdapter(QuestionSettings).validate_python(settings)


class V2ResponseValueValidator:
    """Settings-level value validation reusing v1's per-type validators (spec §17.3).
    span is rejected (deferred); table validates structure only (no Pandera re-run)."""

    @classmethod
    def validate(cls, value, *, type: QuestionType, settings: dict, columns: list[str]) -> None:
        if type in DEFERRED_TYPES:
            raise UnprocessableEntityError(f"question type {type.value!r} (span) is not supported in this release")
        if type == QuestionType.text:
            TextQuestionResponseValueValidator(value).validate()
        elif type == QuestionType.label_selection:
            LabelSelectionQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.multi_label_selection:
            MultiLabelSelectionQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.rating:
            RatingQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.ranking:
            RankingQuestionResponseValueValidator(value).validate_for(_parsed(settings))
        elif type == QuestionType.table:
            cls._validate_table(value, columns)
        else:
            # Defensive: this dispatch is exhaustive for today's QuestionType, but a future
            # enum member wired through without a branch here must fail closed (reject),
            # not silently accept an unvalidated value.
            raise UnprocessableEntityError(f"unknown question type {type!r}; cannot validate value")

    @staticmethod
    def _validate_table(value, columns: list[str]) -> None:
        if not isinstance(value, dict):
            raise UnprocessableEntityError(f"table question expects a dict of values, found {type(value)}")
        bound = set(columns)
        extra = sorted(k for k in value if k not in bound)
        if extra:
            raise UnprocessableEntityError(
                f"table value keys {extra!r} are not bound columns; bound: {sorted(bound)!r}"
            )


class V2SuggestionValidator:
    """Value validation (same as responses) + v1 score-cardinality checks (spec §17.3)."""

    @classmethod
    def validate(cls, value, score, *, type: QuestionType, settings: dict, columns: list[str]) -> None:
        V2ResponseValueValidator.validate(value, type=type, settings=settings, columns=columns)
        cls._validate_score(value, score)

    @staticmethod
    def _validate_score(value, score) -> None:
        if not isinstance(value, list) and isinstance(score, list):
            raise UnprocessableEntityError("a list of scores is not allowed for a single-value suggestion")
        if isinstance(value, list) and score is not None and not isinstance(score, list):
            raise UnprocessableEntityError("a single score is not allowed for a multi-item suggestion value")
        if isinstance(value, list) and isinstance(score, list) and len(value) != len(score):
            raise UnprocessableEntityError("number of items on value and score doesn't match")
