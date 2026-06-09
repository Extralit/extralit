from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User, WorkspaceUser


class WorkspaceUserPolicy:
    @classmethod
    def list(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed

    @classmethod
    async def create(cls, actor: User) -> bool:
        return actor.is_owner

    @classmethod
    def delete(cls, workspace_user: WorkspaceUser) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_user.workspace_id))

        return is_allowed
