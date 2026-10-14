from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models import Webhook

MAXIMUM_NUMBER_OF_WEBHOOKS = 10


class WebhookCreateValidator:
    @classmethod
    async def validate(cls, db: AsyncSession, webhook: Webhook) -> None:
        await cls._validate_maximum_number_of_webhooks(db)

    @classmethod
    async def _validate_maximum_number_of_webhooks(cls, db: AsyncSession) -> None:
        if await cls._count_webhooks(db) >= MAXIMUM_NUMBER_OF_WEBHOOKS:
            raise UnprocessableEntityError(
                f"You can't create more than {MAXIMUM_NUMBER_OF_WEBHOOKS} webhooks. Please delete some of them first"
            )

    @classmethod
    async def _count_webhooks(cls, db: AsyncSession) -> int:
        return (await db.execute(select(func.count(Webhook.id)))).scalar_one()
