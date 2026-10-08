from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.models import Suggestion, UserRole
from extralit_server.search_engine import SearchEngine
from tests.factories import SuggestionFactory, UserFactory

if TYPE_CHECKING:
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestSuiteSuggestions:
    @pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
    async def test_delete_suggestion(
        self, async_client: "AsyncClient", mock_search_engine: SearchEngine, db: "AsyncSession", role: UserRole
    ) -> None:
        suggestion = await SuggestionFactory.create()
        user = await UserFactory.create(role=role, workspaces=[suggestion.record.dataset.workspace])

        response = await async_client.delete(
            f"/api/v1/suggestions/{suggestion.id}",
            headers={API_KEY_HEADER_NAME: user.api_key},
        )

        assert response.status_code == 200

        response_json = response.json()
        assert response_json == {
            "id": str(suggestion.id),
            "question_id": str(suggestion.question_id),
            "type": None,
            "score": None,
            "value": "negative",
            "agent": None,
            "inserted_at": datetime.fromisoformat(response_json["inserted_at"]).isoformat(),
            "updated_at": datetime.fromisoformat(response_json["updated_at"]).isoformat(),
        }

        assert (await db.execute(select(func.count(Suggestion.id)))).scalar() == 0

        mock_search_engine.delete_record_suggestion.assert_called_once_with(suggestion)

    async def test_delete_suggestion_non_existent(self, async_client: "AsyncClient", owner_auth_header: dict) -> None:
        suggestion_id = uuid4()

        response = await async_client.delete(
            f"/api/v1/suggestions/{suggestion_id}",
            headers=owner_auth_header,
        )

        assert response.status_code == 404
        assert response.json() == {"detail": f"Suggestion with id `{suggestion_id}` not found"}

    async def test_delete_suggestion_as_admin_from_another_workspace(self, async_client: "AsyncClient") -> None:
        suggestion = await SuggestionFactory.create()
        user = await UserFactory.create(role=UserRole.admin)

        response = await async_client.delete(
            f"/api/v1/suggestions/{suggestion.id}",
            headers={API_KEY_HEADER_NAME: user.api_key},
        )

        assert response.status_code == 403

    async def test_delete_suggestion_as_annotator(self, async_client: "AsyncClient") -> None:
        suggestion = await SuggestionFactory.create()
        user = await UserFactory.create(role=UserRole.annotator, workspaces=[suggestion.record.dataset.workspace])

        response = await async_client.delete(
            f"/api/v1/suggestions/{suggestion.id}",
            headers={API_KEY_HEADER_NAME: user.api_key},
        )

        assert response.status_code == 403
