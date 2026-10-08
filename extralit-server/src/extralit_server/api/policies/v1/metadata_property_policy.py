from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import MetadataProperty, User


class MetadataPropertyPolicy:
    @classmethod
    def get(cls, metadata_property: MetadataProperty) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (
                actor.role in metadata_property.allowed_roles
                and await actor.is_member(metadata_property.dataset.workspace_id)
            )

        return is_allowed

    @classmethod
    def update(cls, metadata_property: MetadataProperty) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(metadata_property.dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, metadata_property: MetadataProperty) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(metadata_property.dataset.workspace_id))

        return is_allowed
