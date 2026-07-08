from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError

# span is reserved in the enum but deferred to the PDF-chunk design session (spec §17.3).
DEFERRED_TYPES = {QuestionType.span}


class QuestionBindingValidator:
    """Validate a question's column binding against the schema's current columns_cache
    (spec §17.3): existence + arity. Publish-time revalidation and dtype-compat are deferred."""

    @classmethod
    def validate(cls, *, type: QuestionType, columns: list[str], columns_cache: list[dict]) -> None:
        if type in DEFERRED_TYPES:
            raise UnprocessableEntityError(
                f"question type {type.value!r} (span) is not supported in this release; "
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
