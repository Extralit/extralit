import pytest

from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.enums import QuestionType, ResponseStatus, SchemaStatus
from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    UserFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2ResponseFactory,
    V2SuggestionFactory,
)

pytestmark = pytest.mark.asyncio


async def _schema_with_question(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published, workspace__name="wsp")
    version = await SchemaVersionFactory.create(
        schema=schema, columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}]
    )
    schema.current_version_id = version.id
    q = await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    await db.commit()
    return schema, version, q


async def test_cell_resolves_to_suggestion_when_no_response(db):
    schema, version, q = await _schema_with_question(db)
    record = await V2RecordFactory.create(version=version, reference="doc-1")
    await V2SuggestionFactory.create(record=record, question=q, value="flu")
    user = await UserFactory.create()

    view = await projection_ctx.build_reference_view(db, workspace_id=schema.workspace_id, reference="doc-1", user=user)
    cell = view.records[0].cells[0]
    assert cell.value == "flu" and cell.source == "suggestion"


async def test_cell_resolves_to_response_over_suggestion(db):
    schema, version, q = await _schema_with_question(db)
    record = await V2RecordFactory.create(version=version, reference="doc-2")
    await V2SuggestionFactory.create(record=record, question=q, value="flu")
    user = await UserFactory.create()
    await V2ResponseFactory.create(
        record=record, user=user, status=ResponseStatus.submitted, values={"dx": {"value": "covid"}}
    )

    view = await projection_ctx.build_reference_view(db, workspace_id=schema.workspace_id, reference="doc-2", user=user)
    cell = view.records[0].cells[0]
    assert cell.value == "covid" and cell.source == "response"
