from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User
from extralit_server.models.v2 import Schema, V2Question


class V2QuestionPolicy:
    @classmethod
    def list(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(schema.workspace_id)

        return is_allowed

    get = list

    @classmethod
    def create(cls, schema: Schema) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(schema.workspace_id))

        return is_allowed

    @classmethod
    def _write(cls, question: V2Question) -> PolicyAction:
        # `question.schema` must be eagerly loaded (see the router's `selectinload` option) —
        # AsyncSession does not support implicit lazy-loading outside an active greenlet.
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(question.schema.workspace_id))

        return is_allowed

    update = _write
    delete = _write
