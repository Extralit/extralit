from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import Dataset, User


class DatasetPolicy:
    @classmethod
    def list(cls, workspace_id: UUID | None = None) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            if actor.is_owner or workspace_id is None:
                return True

            return await actor.is_member(workspace_id)

        return is_allowed

    @classmethod
    def list_records_with_all_responses(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def get(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(dataset.workspace_id)

        return is_allowed

    @classmethod
    def create(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed

    @classmethod
    def create_field(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def create_question(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def create_metadata_property(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def create_vector_settings(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def create_records(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def update_records(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def upsert_records(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete_records(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def search_records(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or await actor.is_member(dataset.workspace_id)

        return is_allowed

    @classmethod
    def search_records_with_all_responses(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def publish(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def update(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def import_from_hub(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed

    @classmethod
    def export_to_hub(cls, dataset: Dataset) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(dataset.workspace_id))

        return is_allowed
