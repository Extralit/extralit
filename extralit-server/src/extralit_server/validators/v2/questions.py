from pydantic import TypeAdapter, ValidationError

from extralit_server.api.schemas.v1.questions import QuestionSettings
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError

# span is reserved in the enum but deferred to the PDF-chunk design session (spec §17.3).
DEFERRED_TYPES = {QuestionType.span}

# Settings-driven types: their `settings` blob must structurally match v1's QuestionSettings
# union for that type — the SAME shape values.py::_parsed feeds a response/suggestion value
# through at annotation time. `text` has no required settings; `table` is structure-only
# (bound columns, no Pandera re-run); `span` is deferred and already rejected by
# QuestionBindingValidator before settings validation ever runs.
SETTINGS_VALIDATED_TYPES = {
    QuestionType.label_selection,
    QuestionType.multi_label_selection,
    QuestionType.rating,
    QuestionType.ranking,
}


class QuestionBindingValidator:
    """Validate a question's column binding against the schema's current columns_cache
    (spec §17.3): existence + arity. Publish-time revalidation and dtype-compat are deferred."""

    @classmethod
    def validate(cls, *, type: QuestionType, columns: list[str], columns_cache: list[dict]) -> None:
        if type in DEFERRED_TYPES:
            raise UnprocessableEntityError(
                f"question type {type.value!r} is not supported in this release; "
                "it is deferred to the PDF-chunk annotation design"
            )
        if not columns:
            raise UnprocessableEntityError("a question must bind at least one column")
        if type != QuestionType.table and len(columns) != 1:
            raise UnprocessableEntityError(
                f"question type {type.value!r} must bind exactly one column, got {len(columns)}"
            )

        known = {entry["name"] for entry in columns_cache}
        unknown = [name for name in columns if name not in known]
        if unknown:
            raise UnprocessableEntityError(
                f"unknown column(s) {unknown!r} for question binding; available columns: {sorted(known)!r}"
            )


class QuestionSettingsValidator:
    """Validate a question's `settings` blob against its `type` at create/update time
    (spec §17.3). Without this, a settings-driven question (rating/label_selection/
    multi_label_selection/ranking) with empty or malformed settings persists successfully
    but is permanently unusable: every later suggestion/response raises an opaque pydantic
    ValidationError at annotation time instead of failing loudly at create time."""

    @classmethod
    def validate(cls, *, type: QuestionType, settings: dict) -> None:
        if type not in SETTINGS_VALIDATED_TYPES:
            return
        try:
            TypeAdapter(QuestionSettings).validate_python({**settings, "type": type.value})
        except ValidationError as e:
            raise UnprocessableEntityError(f"invalid settings for question type {type.value!r}: {e}") from e
