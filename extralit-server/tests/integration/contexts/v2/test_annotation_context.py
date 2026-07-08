import pytest

from extralit_server.api.schemas.v2.questions import QuestionCreate
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.enums import QuestionType, SchemaStatus
from extralit_server.errors.future import UnprocessableEntityError
from tests.factories import SchemaFactory, SchemaVersionFactory

pytestmark = pytest.mark.asyncio


async def _published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(
        schema=schema,
        columns_cache=[{"name": "disease", "dtype": "str", "nullable": True, "review": None}],
    )
    schema.current_version_id = version.id
    await db.commit()
    return schema


async def test_create_question_validates_binding(db):
    schema = await _published_schema(db)
    q = await annotation_ctx.create_question(
        db,
        schema,
        create=QuestionCreate(
            name="dx",
            title="Diagnosis",
            type=QuestionType.label_selection,
            columns=["disease"],
            settings={"type": "label_selection", "options": [{"value": "x"}]},
        ),
    )
    assert q.id is not None and q.columns == ["disease"]


async def test_create_question_rejects_unknown_column(db):
    schema = await _published_schema(db)
    with pytest.raises(UnprocessableEntityError, match="unknown"):
        await annotation_ctx.create_question(
            db,
            schema,
            create=QuestionCreate(name="bad", title="Bad", type=QuestionType.text, columns=["nope"]),
        )


async def test_create_question_requires_published_schema(db):
    schema = await SchemaFactory.create(status=SchemaStatus.draft)  # current_version_id is None
    with pytest.raises(UnprocessableEntityError, match="published"):
        await annotation_ctx.create_question(
            db,
            schema,
            create=QuestionCreate(name="q", title="Q", type=QuestionType.text, columns=["disease"]),
        )
