from datetime import datetime

import httpx

from extralit_server.contexts import info
from extralit_server.models import Webhook
from extralit_server.webhooks.v1.commons import notify_event


def notify_ping_event(webhook: Webhook) -> httpx.Response:
    return notify_event(
        webhook=webhook,
        event="ping",
        timestamp=datetime.utcnow(),
        data={
            "agent": "extralit-server",
            "version": info.extralit_version(),
        },
    )
