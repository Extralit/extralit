from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import Response, User


class ResponsePolicy:
    @classmethod
    def update(cls, response: Response) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return (
                actor.is_owner
                or actor.id == response.user_id
                or (actor.is_admin and await actor.is_member(response.record.dataset.workspace_id))
            )

        return is_allowed

    @classmethod
    def delete(cls, response: Response) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return (
                actor.is_owner
                or actor.id == response.user_id
                or (actor.is_admin and await actor.is_member(response.record.dataset.workspace_id))
            )

        return is_allowed
