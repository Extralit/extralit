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
        # Additive contract (spec §3.4): a bare dict is the 1-row case; list[dict] is N rows.
        rows = value if isinstance(value, list) else [value]
        bound = set(columns)
        for row in rows:
            if not isinstance(row, dict):
                raise UnprocessableEntityError(f"table question expects a dict of values per row, found {type(row)}")
            extra = sorted(k for k in row if k not in bound)
            if extra:
                raise UnprocessableEntityError(
                    f"table value keys {extra!r} are not bound columns; bound: {sorted(bound)!r}"
                )


class V2SuggestionValidator:
    """Value validation (same as responses) + v1 score-cardinality checks (spec §17.3)."""

    @classmethod
    def validate(cls, value, score, *, type: QuestionType, settings: dict, columns: list[str]) -> None:
        V2ResponseValueValidator.validate(value, type=type, settings=settings, columns=columns)
        cls._validate_score(value, score, type=type)

    @staticmethod
    def _validate_score(value, score, *, type: QuestionType) -> None:
        if type == QuestionType.table:
            # A table value's list is N *rows* (spec §3.4), not N answer choices, so the
            # answer-choice cardinality rules below don't apply. A suggestion's score is
            # whole-suggestion confidence — a scalar or None — which the projection fan-out
            # repeats onto every fanned-out cell. A per-row score list would be a distinct
            # future feature (needing indexed fan-out, not whole-list repetition); reject it
            # now rather than surface an uninterpretable multi-value score in the grid.
            if score is not None and not isinstance(score, (int, float)):
                raise UnprocessableEntityError("a table question score must be a single number or null")
            return
        if not isinstance(value, list) and isinstance(score, list):
            raise UnprocessableEntityError("a list of scores is not allowed for a single-value suggestion")
        if isinstance(value, list) and score is not None and not isinstance(score, list):
            raise UnprocessableEntityError("a single score is not allowed for a multi-item suggestion value")
        if isinstance(value, list) and isinstance(score, list) and len(value) != len(score):
            raise UnprocessableEntityError("number of items on value and score doesn't match")
