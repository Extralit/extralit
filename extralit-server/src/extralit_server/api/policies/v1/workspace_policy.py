from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User


class WorkspacePolicy:
    @classmethod
    def get(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(workspace_id)

        return is_allowed

    @classmethod
    async def create(cls, actor: User) -> bool:
        return actor.is_owner or actor.is_admin

    @classmethod
    async def delete(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    async def list_workspaces_me(cls, actor: User) -> bool:
        return True
