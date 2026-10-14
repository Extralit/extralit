from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User, VectorSettings


class VectorSettingsPolicy:
    @classmethod
    def update(cls, vector_settings: VectorSettings) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(vector_settings.dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, vector_settings: VectorSettings) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(vector_settings.dataset.workspace_id))

        return is_allowed
