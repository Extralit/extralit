from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import WebhookPolicy, authorize
from extralit_server.api.schemas.v1.webhooks import (
    Webhook as WebhookSchema,
)
from extralit_server.api.schemas.v1.webhooks import (
    WebhookCreate as WebhookCreateSchema,
)
from extralit_server.api.schemas.v1.webhooks import (
    Webhooks as WebhooksSchema,
)
from extralit_server.api.schemas.v1.webhooks import (
    WebhookUpdate as WebhookUpdateSchema,
)
from extralit_server.contexts import webhooks
from extralit_server.database import get_async_db
from extralit_server.models import User, Webhook
from extralit_server.security import auth
from extralit_server.webhooks.v1.ping import notify_ping_event

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks", response_model=WebhooksSchema)
async def list_webhooks(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, WebhookPolicy.list)

    return WebhooksSchema(items=await webhooks.list_webhooks(db))


@router.post("/webhooks", status_code=status.HTTP_201_CREATED, response_model=WebhookSchema)
async def create_webhook(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    webhook_create: WebhookCreateSchema,
):
    await authorize(current_user, WebhookPolicy.create)

    return await webhooks.create_webhook(db, webhook_create.model_dump())


@router.patch("/webhooks/{webhook_id}", response_model=WebhookSchema)
async def update_webhook(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    webhook_id: UUID,
    webhook_update: WebhookUpdateSchema,
):
    webhook = await Webhook.get_or_raise(db, webhook_id)

    await authorize(current_user, WebhookPolicy.update)

    return await webhooks.update_webhook(db, webhook, webhook_update.model_dump(exclude_unset=True))


@router.delete("/webhooks/{webhook_id}", response_model=WebhookSchema)
async def delete_webhook(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    webhook_id: UUID,
):
    webhook = await Webhook.get_or_raise(db, webhook_id)

    await authorize(current_user, WebhookPolicy.delete)

    return await webhooks.delete_webhook(db, webhook)


@router.post("/webhooks/{webhook_id}/ping", status_code=status.HTTP_204_NO_CONTENT)
async def ping_webhook(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    webhook_id: UUID,
):
    webhook = await Webhook.get_or_raise(db, webhook_id)

    await authorize(current_user, WebhookPolicy.ping)

    notify_ping_event(webhook)
