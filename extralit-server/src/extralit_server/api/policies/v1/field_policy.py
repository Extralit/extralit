from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import Field, User


class FieldPolicy:
    @classmethod
    def update(cls, field: Field) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(field.dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, field: Field) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(field.dataset.workspace_id))

        return is_allowed
