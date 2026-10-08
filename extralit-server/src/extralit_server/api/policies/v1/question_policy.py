from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import Question, User


class QuestionPolicy:
    @classmethod
    def update(cls, question: Question) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(question.dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, question: Question) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(question.dataset.workspace_id))

        return is_allowed
