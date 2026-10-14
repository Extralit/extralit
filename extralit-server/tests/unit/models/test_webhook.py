import pytest

from tests.factories import WebhookFactory


@pytest.mark.asyncio
class TestWebhook:
    async def test_secret_is_generated_by_default(self):
        webhook = await WebhookFactory.create()

        assert webhook.secret

    async def test_secret_is_generated_by_default_individually(self):
        webhooks = await WebhookFactory.create_batch(2)

        assert webhooks[0].secret != webhooks[1].secret
