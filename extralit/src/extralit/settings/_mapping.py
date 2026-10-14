from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Optional, Union

from extralit._models._settings._mapping import DatasetMappingModel

__all__ = ["DatasetMapping"]


class DatasetMappingBase(ABC):
    """Base class for dataset mapping configurations."""

    def __init__(self, model: DatasetMappingModel):
        self._model = model

    @classmethod
    @abstractmethod
    def from_model(cls, model: DatasetMappingModel) -> "DatasetMappingBase":
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, dict: dict[str, Any]) -> "DatasetMappingBase":
        pass

    @abstractmethod
    def to_dict(self) -> dict[str, Union[str, Sequence[str]]]:
        pass

    @abstractmethod
    def _api_model(self) -> DatasetMappingModel:
        pass


class DatasetMapping(DatasetMappingBase):
    """Dataset mapping configuration wrapper."""

    @classmethod
    def from_model(cls, model: DatasetMappingModel) -> "DatasetMapping":
        return cls(model)

    @classmethod
    def from_dict(cls, dict: dict[str, Any]) -> "DatasetMapping":
        # Check if this is a HubDatasetMapping format (has 'fields' key with list of dicts)
        if "fields" in dict and isinstance(dict["fields"], list) and dict["fields"]:
            return cls.from_model(DatasetMappingModel.from_hub_mapping_dict(dict))
        else:
            # This is the simple key-value mapping format
            return cls.from_model(DatasetMappingModel.from_dict(dict))

    def to_dict(self) -> dict[str, Union[str, Sequence[str]]]:
        return self._model.model_dump()

    def _api_model(self) -> DatasetMappingModel:
        return self._model

    @property
    def fields(self) -> list:
        return self._model.fields

    @property
    def metadata(self) -> list:
        return self._model.metadata or []

    @property
    def suggestions(self) -> list:
        return self._model.suggestions or []

    @property
    def source_id(self) -> Optional[str]:
        return self._model.source_id

    @property
    def target_id(self) -> Optional[str]:
        return self._model.target_id

    def __eq__(self, other):
        """Compare DatasetMapping objects for equality."""
        if not isinstance(other, DatasetMapping):
            return False
        return self._model == other._model
