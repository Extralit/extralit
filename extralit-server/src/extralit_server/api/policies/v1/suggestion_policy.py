from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import Suggestion, User


class SuggestionPolicy:
    @classmethod
    def delete(cls, suggestion: Suggestion) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(suggestion.record.dataset.workspace_id))

        return is_allowed
