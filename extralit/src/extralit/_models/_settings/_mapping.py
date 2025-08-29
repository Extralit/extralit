# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections.abc import Sequence
from typing import Optional, Union

from pydantic import BaseModel, Field

__all__ = ["DatasetMappingItemModel", "DatasetMappingModel"]


class DatasetMappingItemModel(BaseModel):
    """Model for individual mapping items between source and target fields."""

    source: str = Field(..., description="The name of the column in the source dataset")
    target: str = Field(..., description="The name of the target resource in the Extralit dataset")


class DatasetMappingModel(BaseModel):
    """Model for dataset mapping configuration."""

    fields: list[DatasetMappingItemModel] = Field(..., min_length=1, description="Field mappings")
    metadata: Optional[list[DatasetMappingItemModel]] = Field(default=None, description="Metadata mappings")
    suggestions: Optional[list[DatasetMappingItemModel]] = Field(default=None, description="Suggestion mappings")
    source_id: Optional[str] = Field(
        None,
        description="Dataset-level source identifier (format: import:{import_id}, dataset:{dataset_id}, hub:{repo_id})",
    )
    target_id: Optional[str] = Field(None, description="Dataset-level target identifier for workflow tracking")

    def to_dict(self) -> dict[str, Union[str, Sequence[str]]]:
        """Convert mapping to the format expected by Settings class."""
        mapping_dict = {}

        # Add field mappings
        for field_mapping in self.fields:
            mapping_dict[field_mapping.source] = field_mapping.target

        # Add metadata mappings if they exist
        if self.metadata:
            for metadata_mapping in self.metadata:
                mapping_dict[metadata_mapping.source] = metadata_mapping.target

        # Add suggestion mappings if they exist
        if self.suggestions:
            for suggestion_mapping in self.suggestions:
                mapping_dict[suggestion_mapping.source] = suggestion_mapping.target

        return mapping_dict

    @classmethod
    def from_dict(cls, mapping_dict: dict[str, Union[str, Sequence[str]]]) -> "DatasetMappingModel":
        """Create mapping model from dictionary format."""
        fields = []
        metadata = []
        suggestions = []

        for source, target in mapping_dict.items():
            if isinstance(target, str):
                # For now, assume all string targets are fields
                # This could be enhanced with more sophisticated logic
                fields.append(DatasetMappingItemModel(source=source, target=target))
            elif isinstance(target, (list, tuple)):
                # Handle sequence targets - for now treat as fields
                for t in target:
                    fields.append(DatasetMappingItemModel(source=source, target=t))

        return cls(
            fields=fields, metadata=metadata if metadata else None, suggestions=suggestions if suggestions else None
        )

    @classmethod
    def from_hub_mapping_dict(cls, mapping_dict: dict) -> "DatasetMappingModel":
        """Create mapping model from HubDatasetMapping dictionary format."""
        fields = [DatasetMappingItemModel(**item) for item in mapping_dict.get("fields", [])]
        metadata = (
            [DatasetMappingItemModel(**item) for item in mapping_dict.get("metadata", [])]
            if mapping_dict.get("metadata")
            else None
        )
        suggestions = (
            [DatasetMappingItemModel(**item) for item in mapping_dict.get("suggestions", [])]
            if mapping_dict.get("suggestions")
            else None
        )
        source_id = mapping_dict.get("source_id")
        target_id = mapping_dict.get("target_id")

        return cls(fields=fields, metadata=metadata, suggestions=suggestions, source_id=source_id, target_id=target_id)
