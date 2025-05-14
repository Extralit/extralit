
from uuid import UUID

from argilla_server.api.policies.v1.commons import PolicyAction
from argilla_server.models import User

class FilePolicy:
    @classmethod
    def get(cls, workspace_name: str) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member_of_workspace_name(workspace_name)

        return is_allowed
    
    @classmethod
    def list(cls, workspace_name: str) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member_of_workspace_name(workspace_name)

        return is_allowed
    
    @classmethod
    def put_object(cls, workspace_name: str) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (
                actor.is_admin and await actor.is_member_of_workspace_name(workspace_name)
            )

        return is_allowed
        
    @classmethod
    def delete(cls, workspace_name: str) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (
                actor.is_admin and await actor.is_member_of_workspace_name(workspace_name)
            )

        return is_allowed
