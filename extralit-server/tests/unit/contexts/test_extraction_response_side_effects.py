"""Side effects the v2 annotation path deliberately omitted.

contexts/v2/annotation.upsert_response never touched record status and was forbidden
by tests/unit/test_annotation_no_index_import.py from reaching any index. Both are
required behavior; v1's contexts/datasets.upsert_response supplies them. These tests
exist so folding onto v1 cannot silently lose them again.
"""

import pytest

from extralit_server.api.schemas.v1.responses import DraftResponseUpsert, SubmittedResponseUpsert
from extralit_server.contexts import datasets as datasets_ctx
from extralit_server.contexts import distribution as distribution_ctx
from extralit_server.enums import RecordStatus, ResponseStatus
from tests.factories import (
    AnnotatorFactory,
    DatasetFactory,
    QuestionFactory,
    RecordFactory,
    WorkspaceFactory,
)


@pytest.mark.asyncio
class TestExtractionResponseSideEffects:
    async def _setup(self, db, mocker):
        # `distribution.update_record_status` (invoked by `upsert_response`) opens its own
        # DB session via `distribution._get_async_db`, independent of the `db` fixture's
        # session. That session runs on a separate connection and cannot see data created
        # inside the test's nested transaction, so it 404s on the record we just made.
        # Point it at the same session the test uses, mirroring what the `async_client`
        # fixture does for API-level tests (tests/unit/conftest.py).
        async def override_get_async_db(isolation_level=None):
            yield db

        mocker.patch.object(distribution_ctx, "_get_async_db", override_get_async_db)

        workspace = await WorkspaceFactory.create()
        dataset = await DatasetFactory.create(
            workspace=workspace, status="ready", distribution={"strategy": "overlap", "min_submitted": 1}
        )
        question = await QuestionFactory.create(
            dataset=dataset, name="population", settings={"type": "text", "use_markdown": False}
        )
        record = await RecordFactory.create(dataset=dataset, reference="10.1000/j.foo.2020.01")
        user = await AnnotatorFactory.create(workspaces=[workspace])

        await datasets_ctx.preload_records_relationships_before_validate(db, [record])

        return dataset, question, record, user

    async def test_submitting_a_response_completes_the_record(self, db, mock_search_engine, mocker):
        _dataset, _question, record, user = await self._setup(db, mocker)
        assert record.status == RecordStatus.pending

        await datasets_ctx.upsert_response(
            db,
            mock_search_engine,
            record,
            user,
            SubmittedResponseUpsert(
                record_id=record.id,
                status=ResponseStatus.submitted,
                values={"population": {"value": "Kenya"}},
            ),
        )

        await db.refresh(record)
        assert record.status == RecordStatus.completed

    async def test_a_draft_response_leaves_the_record_pending(self, db, mock_search_engine, mocker):
        _dataset, _question, record, user = await self._setup(db, mocker)

        await datasets_ctx.upsert_response(
            db,
            mock_search_engine,
            record,
            user,
            DraftResponseUpsert(
                record_id=record.id,
                status=ResponseStatus.draft,
                values={"population": {"value": "Kenya"}},
            ),
        )

        await db.refresh(record)
        assert record.status == RecordStatus.pending

    async def test_submitting_a_response_reaches_the_search_index(self, db, mock_search_engine, mocker):
        _dataset, _question, record, user = await self._setup(db, mocker)

        await datasets_ctx.upsert_response(
            db,
            mock_search_engine,
            record,
            user,
            SubmittedResponseUpsert(
                record_id=record.id,
                status=ResponseStatus.submitted,
                values={"population": {"value": "Kenya"}},
            ),
        )

        mock_search_engine.update_record_response.assert_awaited()

    async def test_upserting_a_suggestion_reaches_the_search_index(self, db, mock_search_engine, mocker):
        from extralit_server.api.schemas.v1.suggestions import SuggestionCreate

        _dataset, question, record, _user = await self._setup(db, mocker)

        await datasets_ctx.upsert_suggestion(
            db,
            mock_search_engine,
            record,
            question,
            SuggestionCreate(question_id=question.id, value="Kenya", agent="gpt-x", score=0.9),
        )

        mock_search_engine.update_record_suggestion.assert_awaited()
