from extralit_server.models import User


class WebhookPolicy:
    @classmethod
    async def list(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    async def create(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    async def update(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    async def delete(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    async def ping(cls, actor: User) -> bool:
        return actor.is_owner
