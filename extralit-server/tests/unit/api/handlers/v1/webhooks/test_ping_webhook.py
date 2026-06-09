import json
from uuid import UUID, uuid4

import pytest
import respx
from httpx import AsyncClient, Response
from standardwebhooks.webhooks import Webhook

from extralit_server.constants import API_KEY_HEADER_NAME
from extralit_server.contexts import info
from tests.factories import AdminFactory, AnnotatorFactory, WebhookFactory


@pytest.mark.asyncio
class TestPingWebhook:
    def url(self, webhook_id: UUID) -> str:
        return f"/api/v1/webhooks/{webhook_id}/ping"

    async def test_ping_webhook(self, async_client: AsyncClient, owner_auth_header: dict, respx_mock):
        webhook = await WebhookFactory.create()

        respx_mock.post(webhook.url).mock(return_value=Response(200))
        response = await async_client.post(
            self.url(webhook.id),
            headers=owner_auth_header,
        )

        assert response.status_code == 204

        request, _ = respx.calls.last
        timestamp = json.loads(request.content)["timestamp"]

        wh = Webhook(webhook.secret)
        assert wh.verify(headers=request.headers, data=request.content) == {
            "type": "ping",
            "version": 1,
            "timestamp": timestamp,
            "data": {
                "agent": "extralit-server",
                "version": info.extralit_version(),
            },
        }

    async def test_ping_webhook_as_admin(self, async_client: AsyncClient, respx_mock):
        admin = await AdminFactory.create()
        webhook = await WebhookFactory.create()

        respx_mock.post(webhook.url).mock(return_value=Response(200))
        response = await async_client.post(
            self.url(webhook.id),
            headers={API_KEY_HEADER_NAME: admin.api_key},
        )

        assert response.status_code == 403

    async def test_ping_webhook_as_annotator(self, async_client: AsyncClient):
        annotator = await AnnotatorFactory.create()
        webhook = await WebhookFactory.create()

        response = await async_client.post(
            self.url(webhook.id),
            headers={API_KEY_HEADER_NAME: annotator.api_key},
        )

        assert response.status_code == 403

    async def test_ping_webhook_without_authentication(self, async_client: AsyncClient):
        webhook = await WebhookFactory.create()

        response = await async_client.post(self.url(webhook.id))

        assert response.status_code == 401

    async def test_ping_webhook_with_nonexistent_webhook_id(self, async_client: AsyncClient, owner_auth_header: dict):
        webhook_id = uuid4()

        response = await async_client.post(
            self.url(webhook_id),
            headers=owner_auth_header,
        )

        assert response.status_code == 404
        assert response.json() == {"detail": f"Webhook with id `{webhook_id}` not found"}
