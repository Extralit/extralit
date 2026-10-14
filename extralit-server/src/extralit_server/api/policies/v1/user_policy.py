from extralit_server.models import User


class UserPolicy:
    @classmethod
    async def get(cls, actor: User) -> bool:
        return actor.is_owner

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
    async def list_workspaces(cls, actor: User) -> bool:
        return actor.is_owner
