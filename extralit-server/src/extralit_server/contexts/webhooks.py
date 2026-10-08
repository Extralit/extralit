from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.models import Webhook
from extralit_server.validators.webhooks import WebhookCreateValidator


async def list_webhooks(db: AsyncSession) -> Sequence[Webhook]:
    result = await db.execute(select(Webhook).order_by(Webhook.inserted_at.asc()))

    return result.scalars().all()


async def list_enabled_webhooks(db: AsyncSession) -> Sequence[Webhook]:
    result = await db.execute(select(Webhook).where(Webhook.enabled).order_by(Webhook.inserted_at.asc()))

    return result.scalars().all()


async def create_webhook(db: AsyncSession, webhook_attrs: dict) -> Webhook:
    webhook = Webhook(**webhook_attrs)

    await WebhookCreateValidator.validate(db, webhook)

    return await webhook.save(db)


async def update_webhook(db: AsyncSession, webhook: Webhook, webhook_attrs: dict) -> Webhook:
    return await webhook.update(db, **webhook_attrs)


async def delete_webhook(db: AsyncSession, webhook: Webhook) -> Webhook:
    return await webhook.delete(db)
