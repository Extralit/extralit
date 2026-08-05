"""The table-question carve-out in `SuggestionCreateValidator._validate_score`.

Ported from the deleted `validators/v2/values.py::V2SuggestionValidator._validate_score`
during the v2->v1 fold. A table value's list is N *rows*, not N answer choices, so the
generic answer-choice cardinality rules must not apply to it — without this carve-out the
ordinary case (a multi-row value with one whole-suggestion confidence score) would 422.

Note: v1's `SuggestionCreate.value` union does not yet accept table rows (list[dict]),
so these tests drive the branch with a plain `list[str]` value. Extending the value union
to carry table rows belongs with the table-question work; until then a table suggestion
cannot be constructed through v1 schemas at all, so this validator branch is the piece
that must be in place first rather than the whole path.
"""

import pytest

from extralit_server.api.schemas.v1.questions import TableQuestionSettings, TextQuestionSettings
from extralit_server.api.schemas.v1.suggestions import SuggestionCreate
from extralit_server.enums import QuestionType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.validators.suggestions import SuggestionCreateValidator
from tests.factories import RecordFactory


def _suggestion(question_id, value, score):
    return SuggestionCreate(question_id=question_id, value=value, score=score, agent="agent-x")


@pytest.mark.asyncio
class TestTableSuggestionScore:
    async def test_a_scalar_score_is_allowed_for_a_multi_item_table_value(self, db):
        record = await RecordFactory.create()
        settings = TableQuestionSettings(type=QuestionType.table)
        suggestion = _suggestion(record.id, ["row-1", "row-2"], 0.92)

        # Must not raise: two rows, one whole-suggestion confidence score. The generic
        # cardinality rule would reject this pairing.
        SuggestionCreateValidator._validate_score(suggestion, settings)

    async def test_a_null_score_is_allowed_for_a_table_value(self, db):
        record = await RecordFactory.create()
        settings = TableQuestionSettings(type=QuestionType.table)

        SuggestionCreateValidator._validate_score(_suggestion(record.id, ["row-1"], None), settings)

    async def test_a_list_score_is_rejected_for_a_table_value(self, db):
        record = await RecordFactory.create()
        settings = TableQuestionSettings(type=QuestionType.table)
        suggestion = _suggestion(record.id, ["row-1", "row-2"], [0.1, 0.2])

        with pytest.raises(UnprocessableEntityError, match=r"table question score must be a single number"):
            SuggestionCreateValidator._validate_score(suggestion, settings)

    async def test_non_table_questions_keep_the_cardinality_rule(self, db):
        record = await RecordFactory.create()
        settings = TextQuestionSettings(type=QuestionType.text, use_markdown=False)
        suggestion = _suggestion(record.id, ["a", "b"], 0.92)

        with pytest.raises(UnprocessableEntityError, match=r"single score value is not allowed"):
            SuggestionCreateValidator._validate_score(suggestion, settings)
