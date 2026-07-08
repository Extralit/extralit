import pytest

from extralit_server.api.schemas.v2.annotation import ResponseUpsert, SuggestionUpsert
from extralit_server.api.schemas.v2.questions import QuestionCreate, QuestionUpdate
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.enums import QuestionType, ResponseStatus, SchemaStatus, V2RecordStatus
from extralit_server.errors.future import UnprocessableEntityError
from tests.factories import SchemaFactory, SchemaVersionFactory, UserFactory, V2QuestionFactory, V2RecordFactory

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


async def test_update_question_columns_revalidates_binding(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(
        schema=schema,
        columns_cache=[
            {"name": "disease", "dtype": "str", "nullable": True, "review": None},
            {"name": "outcome", "dtype": "str", "nullable": True, "review": None},
        ],
    )
    schema.current_version_id = version.id
    await db.commit()

    question = await annotation_ctx.create_question(
        db,
        schema,
        create=QuestionCreate(name="dx", title="Dx", type=QuestionType.text, columns=["disease"]),
    )

    updated = await annotation_ctx.update_question(db, question, update=QuestionUpdate(columns=["outcome"]))
    assert updated.columns == ["outcome"]


async def test_update_question_rejects_unknown_column(db):
    schema = await _published_schema(db)
    question = await annotation_ctx.create_question(
        db,
        schema,
        create=QuestionCreate(name="dx", title="Dx", type=QuestionType.text, columns=["disease"]),
    )

    with pytest.raises(UnprocessableEntityError, match="unknown"):
        await annotation_ctx.update_question(db, question, update=QuestionUpdate(columns=["nope"]))


async def test_update_question_rejects_arity_mismatch_for_non_table_type(db):
    schema = await SchemaFactory.create(status=SchemaStatus.published)
    version = await SchemaVersionFactory.create(
        schema=schema,
        columns_cache=[
            {"name": "disease", "dtype": "str", "nullable": True, "review": None},
            {"name": "outcome", "dtype": "str", "nullable": True, "review": None},
        ],
    )
    schema.current_version_id = version.id
    await db.commit()

    question = await annotation_ctx.create_question(
        db,
        schema,
        create=QuestionCreate(name="dx", title="Dx", type=QuestionType.text, columns=["disease"]),
    )

    with pytest.raises(UnprocessableEntityError, match="exactly one column"):
        await annotation_ctx.update_question(db, question, update=QuestionUpdate(columns=["disease", "outcome"]))


async def test_upsert_suggestion_is_idempotent_per_record_question(db):
    schema = await _published_schema(db)
    question = await V2QuestionFactory.create(
        schema=schema, type=QuestionType.text, columns=["disease"], settings={"type": "text"}
    )
    record = await V2RecordFactory.create(version__schema=schema)

    s1 = await annotation_ctx.upsert_suggestion(
        db, record, question, upsert=SuggestionUpsert(question_id=question.id, value="a")
    )
    s2 = await annotation_ctx.upsert_suggestion(
        db, record, question, upsert=SuggestionUpsert(question_id=question.id, value="b")
    )
    assert s1.id == s2.id and s2.value == "b"


async def test_upsert_response_keyed_by_question_no_record_status_change(db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}, required=True
    )
    record = await V2RecordFactory.create(version__schema=schema, status=V2RecordStatus.pending)
    user = await UserFactory.create()

    resp = await annotation_ctx.upsert_response(
        db, record, user, upsert=ResponseUpsert(status=ResponseStatus.submitted, values={"dx": {"value": "flu"}})
    )
    assert resp.values == {"dx": {"value": "flu"}}
    assert record.status == V2RecordStatus.pending  # spec §17.3: no status side-effect


async def test_submitted_response_requires_required_question(db):
    schema = await _published_schema(db)
    await V2QuestionFactory.create(
        schema=schema, name="dx", type=QuestionType.text, columns=["disease"], settings={"type": "text"}, required=True
    )
    # A second, optional question (also bound to "disease" — binding validation allows reuse) so the
    # payload can be non-empty while omitting the required one. Submitting empty values would trip the
    # earlier "missing response values" guard instead of the required-question path under test.
    await V2QuestionFactory.create(
        schema=schema,
        name="notes",
        type=QuestionType.text,
        columns=["disease"],
        settings={"type": "text"},
        required=False,
    )
    record = await V2RecordFactory.create(version__schema=schema)
    user = await UserFactory.create()

    with pytest.raises(UnprocessableEntityError, match="required"):
        await annotation_ctx.upsert_response(
            db,
            record,
            user,
            upsert=ResponseUpsert(status=ResponseStatus.submitted, values={"notes": {"value": "n"}}),
        )
