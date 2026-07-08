from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User
from extralit_server.models.v2 import Schema, V2Question, V2Record


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


class V2SuggestionPolicy:
    @classmethod
    def read(cls, record: "V2Record") -> PolicyAction:
        # `record.schema` must be eagerly loaded (see the router's `selectinload` option) —
        # AsyncSession does not support implicit lazy-loading outside an active greenlet.
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed

    @classmethod
    def write(cls, record: "V2Record") -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(record.schema.workspace_id))

        return is_allowed


class V2ResponsePolicy:
    """Own-response authz (spec §17.5), ported from v1 ResponsePolicy with the workspace
    resolved via record.schema.workspace_id."""

    @classmethod
    def read(cls, record: "V2Record") -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed

    @classmethod
    def upsert_own(cls, record: "V2Record") -> PolicyAction:
        # PUT writes the current user's own response; any workspace member (incl. annotators)
        # may write their own, matching v1 (actor.id == response.user_id).
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(record.schema.workspace_id)

        return is_allowed
