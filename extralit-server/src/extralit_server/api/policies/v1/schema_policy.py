from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User
from extralit_server.models.v2 import Schema


class SchemaPolicy:
    @classmethod
    def list(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(workspace_id)

        return is_allowed

    @classmethod
    def create(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed

    @classmethod
    def get(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(schema.workspace_id)

        return is_allowed

    @classmethod
    def update(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(schema.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(schema.workspace_id))

        return is_allowed

    @classmethod
    def publish(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(schema.workspace_id))

        return is_allowed
