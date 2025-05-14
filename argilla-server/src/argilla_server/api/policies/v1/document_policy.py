
from uuid import UUID

from argilla_server.api.policies.v1.commons import PolicyAction
from argilla_server.models import User

class DocumentPolicy:
    @classmethod
    def create(cls) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or actor.is_admin or actor.is_annotator

        return is_allowed
    
    @classmethod
    def get(cls) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            # TODO check if the user has access to the workspace
            return actor.is_owner or actor.is_admin or actor.is_annotator

        return is_allowed
    
    @classmethod
    def delete(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed
    
    @classmethod
    def list(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed
        
