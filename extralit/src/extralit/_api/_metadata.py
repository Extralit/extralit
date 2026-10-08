import builtins
from uuid import UUID

import httpx

from extralit._api._base import ResourceAPI
from extralit._exceptions import api_error_handler
from extralit._models import MetadataFieldModel

__all__ = ["MetadataAPI"]


class MetadataAPI(ResourceAPI[MetadataFieldModel]):
    """Manage metadata via the API"""

    http_client: httpx.Client

    ################
    # CRUD methods #
    ################

    @api_error_handler
    def get(self, metadata_id: UUID) -> MetadataFieldModel:
        raise NotImplementedError()

    @api_error_handler
    def create(self, metadata: MetadataFieldModel) -> MetadataFieldModel:
        url = f"/api/v1/datasets/{metadata.dataset_id}/metadata-properties"
        response = self.http_client.post(url=url, json=metadata.model_dump())
        response.raise_for_status()
        response_json = response.json()
        created_metadata = self._model_from_json(response_json=response_json)
        self._log_message(message=f"Created metadata field {created_metadata.name} in dataset {metadata.dataset_id}")
        return created_metadata

    @api_error_handler
    def update(self, metadata: MetadataFieldModel) -> MetadataFieldModel:
        url = f"/api/v1/metadata-properties/{metadata.id}"
        response = self.http_client.patch(url=url, json=metadata.model_dump())
        response.raise_for_status()
        response_json = response.json()
        updated_metadata = self._model_from_json(response_json=response_json)
        self._log_message(message=f"Updated metadata field {updated_metadata.name}")
        return updated_metadata

    def delete(self, metadata_id: UUID) -> None:
        url = f"/api/v1/metadata-properties/{metadata_id}"
        self.http_client.delete(url=url).raise_for_status()
        self._log_message(message=f"Deleted metadata field {metadata_id}")

    ####################
    # Utility methods #
    ####################

    @api_error_handler
    def list(self, dataset_id: UUID) -> list[MetadataFieldModel]:
        response = self.http_client.get(f"/api/v1/me/datasets/{dataset_id}/metadata-properties")
        response.raise_for_status()
        response_json = response.json()
        return self._model_from_jsons(response_jsons=response_json["items"])

    ####################
    # Private methods #
    ####################

    def _model_from_json(self, response_json: dict) -> MetadataFieldModel:
        return MetadataFieldModel(**response_json)

    def _model_from_jsons(self, response_jsons: builtins.list[dict]) -> builtins.list[MetadataFieldModel]:
        return list(map(self._model_from_json, response_jsons))
