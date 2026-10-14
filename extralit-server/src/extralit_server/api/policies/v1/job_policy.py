from extralit_server.models import User


class JobPolicy:
    @classmethod
    async def get(cls, actor: User) -> bool:
        return actor.is_owner or actor.is_admin
