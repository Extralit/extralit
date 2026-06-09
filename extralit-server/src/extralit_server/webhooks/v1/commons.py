import json
import secrets
from datetime import datetime, timezone
from math import floor

import httpx
from standardwebhooks.webhooks import Webhook

from extralit_server.models import Webhook as WebhookModel

MSG_ID_BYTES_LENGTH = 16

NOTIFY_EVENT_DEFAULT_TIMEOUT = httpx.Timeout(timeout=20.0)


# NOTE: We are using standard webhooks implementation.
# For more information take a look to https://www.standardwebhooks.com
def notify_event(webhook: WebhookModel, event: str, timestamp: datetime, data: dict) -> httpx.Response:
    timestamp_attempt = datetime.utcnow()

    msg_id = _generate_msg_id()
    payload = json.dumps(_build_payload(event, timestamp, data))
    signature = Webhook(webhook.secret).sign(msg_id, timestamp_attempt, payload)

    return httpx.post(
        webhook.url,
        headers=_build_headers(msg_id, timestamp_attempt, signature),
        content=payload,
        timeout=NOTIFY_EVENT_DEFAULT_TIMEOUT,
    )


def _generate_msg_id() -> str:
    return f"msg_{secrets.token_urlsafe(MSG_ID_BYTES_LENGTH)}"


def _build_headers(msg_id: str, timestamp: datetime, signature: str) -> dict:
    return {
        "webhook-id": msg_id,
        "webhook-timestamp": str(floor(timestamp.replace(tzinfo=timezone.utc).timestamp())),
        "webhook-signature": signature,
        "content-type": "application/json",
    }


def _build_payload(type: str, timestamp: datetime, data: dict) -> dict:
    return {
        "type": type,
        "version": 1,
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "data": data,
    }
