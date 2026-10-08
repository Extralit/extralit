import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.models import Question
from tests.factories import DatasetFactory, FieldFactory, TextQuestionFactory


@pytest.mark.asyncio
class TestQuestionColumnBinding:
    async def _dataset_with_columns(self, *names):
        dataset = await DatasetFactory.create()
        for name in names:
            await FieldFactory.create(
                dataset=dataset, name=name, settings={"type": "column", "dtype": "string", "nullable": True}
            )
        return dataset

    async def test_question_binds_to_a_declared_column(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("population")
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={
                "name": "population_review",
                "title": "Population",
                "settings": {"type": "text", "use_markdown": False, "columns": ["population"]},
            },
        )
        assert response.status_code == 201, response.json()
        assert response.json()["settings"]["columns"] == ["population"]

    async def test_binding_to_an_undeclared_column_is_rejected(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("population")
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={
                "name": "q",
                "title": "Q",
                "settings": {"type": "text", "use_markdown": False, "columns": ["nope"]},
            },
        )
        assert response.status_code == 422
        assert "nope" in response.text

    async def test_a_scalar_question_binds_to_exactly_one_column(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("a", "b")
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={
                "name": "q",
                "title": "Q",
                "settings": {"type": "text", "use_markdown": False, "columns": ["a", "b"]},
            },
        )
        assert response.status_code == 422

    async def test_a_table_question_binds_to_many_columns(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("a", "b")
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={
                "name": "t",
                "title": "T",
                "settings": {"type": "table", "columns": ["a", "b"]},
            },
        )
        assert response.status_code == 201, response.json()
        assert response.json()["settings"]["columns"] == ["a", "b"]

    async def test_an_empty_binding_is_rejected(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("a")
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={"name": "q", "title": "Q", "settings": {"type": "table", "columns": []}},
        )
        assert response.status_code == 422

    async def test_questions_without_a_binding_are_still_valid(self, async_client, owner_auth_header):
        # A plain annotation dataset has no column fields and no bindings — unchanged v1 behavior.
        dataset = await DatasetFactory.create()
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/questions",
            headers=owner_auth_header,
            json={"name": "q", "title": "Q", "settings": {"type": "text", "use_markdown": False}},
        )
        assert response.status_code == 201, response.json()

    async def test_patch_sets_a_valid_column_binding(self, db: AsyncSession, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("population")
        question = await TextQuestionFactory.create(dataset=dataset)

        response = await async_client.patch(
            f"/api/v1/questions/{question.id}",
            headers=owner_auth_header,
            json={"settings": {"type": "text", "use_markdown": False, "columns": ["population"]}},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["settings"]["columns"] == ["population"]

        # Don't trust the response body alone — re-read the stored binding from the DB.
        stored = await db.get(Question, question.id)
        assert stored.settings.get("columns") == ["population"]

    async def test_patch_rejects_an_invalid_column_binding(self, db: AsyncSession, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("population")
        question = await TextQuestionFactory.create(dataset=dataset)

        response = await async_client.patch(
            f"/api/v1/questions/{question.id}",
            headers=owner_auth_header,
            json={"settings": {"type": "text", "use_markdown": False, "columns": ["nope"]}},
        )
        assert response.status_code == 422
        assert "nope" in response.text

        # The rejected binding must not have been persisted.
        stored = await db.get(Question, question.id)
        assert stored.settings.get("columns") is None

    async def test_patch_enforces_the_scalar_arity_rule(self, async_client, owner_auth_header):
        dataset = await self._dataset_with_columns("a", "b")
        question = await TextQuestionFactory.create(dataset=dataset)

        response = await async_client.patch(
            f"/api/v1/questions/{question.id}",
            headers=owner_auth_header,
            json={"settings": {"type": "text", "use_markdown": False, "columns": ["a", "b"]}},
        )
        assert response.status_code == 422
