import json

import pytest
import respx
from httpx import Response
from standardwebhooks.webhooks import Webhook

from extralit_server.contexts import info
from extralit_server.webhooks.v1.ping import notify_ping_event
from tests.factories import WebhookFactory


@pytest.mark.asyncio
class TestNotifyPingEvent:
    async def test_notify_ping_event(self, respx_mock):
        webhook = await WebhookFactory.create()

        respx_mock.post(webhook.url).mock(return_value=Response(200))
        response = notify_ping_event(webhook)

        assert response.status_code == 200

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
