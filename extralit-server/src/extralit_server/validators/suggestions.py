from extralit_server.api.schemas.v1.questions import QuestionSettings
from extralit_server.api.schemas.v1.suggestions import SuggestionCreate
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.database import Record
from extralit_server.validators.response_values import ResponseValueValidator


class SuggestionCreateValidator:
    @classmethod
    def validate(cls, suggestion_create: SuggestionCreate, question_settings: QuestionSettings, record: Record) -> None:
        cls._validate_value(suggestion_create, question_settings, record)
        cls._validate_score(suggestion_create, question_settings)

    @staticmethod
    def _validate_value(
        suggestion_create: SuggestionCreate, question_settings: QuestionSettings, record: Record
    ) -> None:
        ResponseValueValidator.validate(suggestion_create.value, question_settings, record)

    @classmethod
    def _validate_score(cls, suggestion_create: SuggestionCreate, question_settings: QuestionSettings):
        if getattr(question_settings, "type", None) == QuestionType.table:
            # A table value's list is N *rows*, not N answer choices, so the answer-choice
            # cardinality rules below don't apply. A suggestion's score is whole-suggestion
            # confidence — a scalar or None — which the projection fan-out repeats onto every
            # fanned-out cell. A per-row score list would be a distinct future feature (needing
            # indexed fan-out, not whole-list repetition); reject it now rather than surface an
            # uninterpretable multi-value score in the grid.
            if suggestion_create.score is not None and not isinstance(suggestion_create.score, (int, float)):
                raise UnprocessableEntityError("a table question score must be a single number or null")
            return

        cls._validate_value_and_score_cardinality(suggestion_create)
        cls._validate_value_and_score_have_same_length(suggestion_create)

    @staticmethod
    def _validate_value_and_score_cardinality(suggestion_create: SuggestionCreate):
        if not isinstance(suggestion_create.value, list) and isinstance(suggestion_create.score, list):
            raise UnprocessableEntityError("a list of score values is not allowed for a suggestion with a single value")

        if (
            isinstance(suggestion_create.value, list)
            and suggestion_create.score is not None
            and not isinstance(suggestion_create.score, list)
        ):
            raise UnprocessableEntityError(
                "a single score value is not allowed for a suggestion with a multiple items value"
            )

    @staticmethod
    def _validate_value_and_score_have_same_length(suggestion_create: SuggestionCreate) -> None:
        if not isinstance(suggestion_create.value, list) or not isinstance(suggestion_create.score, list):
            return

        if len(suggestion_create.value) != len(suggestion_create.score):
            raise UnprocessableEntityError("number of items on value and score attributes doesn't match")
