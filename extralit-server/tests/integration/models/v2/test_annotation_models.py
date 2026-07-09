import pytest
from sqlalchemy.exc import IntegrityError

from extralit_server.enums import QuestionType, ResponseStatus
from tests.factories import (
    SchemaFactory,
    UserFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2ResponseFactory,
    V2SuggestionFactory,
)


@pytest.mark.asyncio
async def test_question_persists_with_type_and_columns(db):
    q = await V2QuestionFactory.create(type=QuestionType.label_selection, columns=["disease"])
    assert q.id is not None
    assert q.type == QuestionType.label_selection
    assert q.columns == ["disease"]


@pytest.mark.asyncio
async def test_question_name_unique_per_schema(db):
    # Same schema OBJECT passed twice (not schema_id) so the (schema_id, name) constraint trips.
    schema = await SchemaFactory.create()
    await V2QuestionFactory.create(schema=schema, name="dup")
    with pytest.raises(IntegrityError):
        await V2QuestionFactory.create(schema=schema, name="dup")


@pytest.mark.asyncio
async def test_suggestion_unique_per_record_question(db):
    # Pass the parent OBJECTS (not *_id): the factories declare record/question as SubFactory
    # defaults, so passing only ids would let factory-boy create fresh parents and the
    # relationship would win on flush — the (record_id, question_id) constraint would never trip.
    record = await V2RecordFactory.create()
    question = await V2QuestionFactory.create()
    await V2SuggestionFactory.create(record=record, question=question)
    with pytest.raises(IntegrityError):
        await V2SuggestionFactory.create(record=record, question=question)


@pytest.mark.asyncio
async def test_response_unique_per_record_user(db):
    record = await V2RecordFactory.create()
    user = await UserFactory.create()
    r = await V2ResponseFactory.create(
        record=record, user=user, status=ResponseStatus.submitted, values={"q": {"value": "x"}}
    )
    assert r.is_submitted
    with pytest.raises(IntegrityError):
        await V2ResponseFactory.create(record=record, user=user)
