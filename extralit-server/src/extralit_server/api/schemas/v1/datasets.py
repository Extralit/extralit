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

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, constr, model_validator
from pydantic.v1.utils import GetterDict

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.enums import DatasetDistributionStrategy, DatasetStatus

try:
    from typing import Annotated
except ImportError:
    from typing import Annotated

DATASET_NAME_MIN_LENGTH = 1
DATASET_NAME_MAX_LENGTH = 200
DATASET_GUIDELINES_MIN_LENGTH = 1
DATASET_GUIDELINES_MAX_LENGTH = 10000

DatasetName = Annotated[
    constr(
        min_length=DATASET_NAME_MIN_LENGTH,
        max_length=DATASET_NAME_MAX_LENGTH,
    ),
    Field(..., description="Dataset name"),
]

DatasetGuidelines = Annotated[
    constr(min_length=DATASET_GUIDELINES_MIN_LENGTH, max_length=DATASET_GUIDELINES_MAX_LENGTH),
    Field(..., description="Dataset guidelines"),
]


class DatasetOverlapDistribution(BaseModel):
    strategy: Literal[DatasetDistributionStrategy.overlap]
    min_submitted: int


DatasetDistribution = DatasetOverlapDistribution


class DatasetOverlapDistributionCreate(BaseModel):
    strategy: Literal[DatasetDistributionStrategy.overlap]
    min_submitted: int = Field(
        ge=1,
        description="Minimum number of submitted responses to consider a record as completed",
    )


DatasetDistributionCreate = DatasetOverlapDistributionCreate


class DatasetOverlapDistributionUpdate(DatasetDistributionCreate):
    pass


DatasetDistributionUpdate = DatasetOverlapDistributionUpdate


class ResponseMetrics(BaseModel):
    total: int
    submitted: int
    discarded: int
    draft: int
    pending: int


class DatasetMetrics(BaseModel):
    responses: ResponseMetrics


class RecordResponseDistribution(BaseModel):
    submitted: int = 0
    discarded: int = 0
    draft: int = 0


class UserProgress(BaseModel):
    username: str
    completed: RecordResponseDistribution = RecordResponseDistribution()
    pending: RecordResponseDistribution = RecordResponseDistribution()

    model_config = ConfigDict(from_attributes=True)


class DatasetProgress(BaseModel):
    total: int
    completed: int
    pending: int
    users: list[UserProgress] = Field(default_factory=list)


class UsersProgress(BaseModel):
    users: list[UserProgress]


class DatasetGetterDict(GetterDict):
    def get(self, key: Any, default: Any = None) -> Any:
        if key == "metadata":
            return getattr(self._obj, "metadata_", None)
        elif key == "mapping":
            metadata = getattr(self._obj, "metadata_", None)
            if metadata and "mapping" in metadata:
                try:
                    return DatasetMapping.model_validate(metadata["mapping"])
                except Exception:
                    return None
            return None

        return super().get(key, default)


class Dataset(BaseModel):
    id: UUID
    name: str
    guidelines: str | None = None
    allow_extra_metadata: bool
    status: DatasetStatus
    distribution: DatasetDistribution
    metadata: dict[str, Any] | None = None
    mapping: "DatasetMapping | None" = None
    workspace_id: UUID
    last_activity_at: datetime
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def validate(cls, value) -> dict:
        getter = DatasetGetterDict(value)

        data = {}
        for field in cls.model_fields:
            data[field] = getter.get(field)

        return data


class Datasets(BaseModel):
    items: list[Dataset]

    def get_compatible_datasets(self, column_names: list[str]) -> "Datasets":
        """
        Filter datasets that have compatible mappings based on overlapping column names
        """
        compatible_datasets = []
        column_names_set = set(column_names)

        for dataset in self.items:
            # The Dataset schema automatically parses mapping from metadata_
            if not dataset.mapping:
                continue

            # Get all source column names from the mapping
            mapping_sources = set(dataset.mapping.sources)

            # Calculate overlap - require at least 50% overlap
            if mapping_sources and column_names_set:
                overlap = len(column_names_set.intersection(mapping_sources))
                compatibility_score = overlap / len(column_names_set)

                if compatibility_score >= 0.5:  # At least 50% compatibility
                    compatible_datasets.append(dataset)

        return Datasets(items=compatible_datasets)


class DatasetCreate(BaseModel):
    name: DatasetName
    guidelines: DatasetGuidelines | None = None
    allow_extra_metadata: bool = True
    distribution: DatasetDistributionCreate = DatasetOverlapDistributionCreate(
        strategy=DatasetDistributionStrategy.overlap,
        min_submitted=1,
    )
    metadata: dict[str, Any] | None = None
    workspace_id: UUID


class DatasetUpdate(UpdateSchema):
    name: DatasetName | None = None
    guidelines: DatasetGuidelines | None = None
    allow_extra_metadata: bool | None = None
    distribution: DatasetDistributionUpdate | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")

    __non_nullable_fields__ = {"name", "allow_extra_metadata", "distribution"}


class DatasetMappingItem(BaseModel):
    source: str = Field(..., description="The name of the column in the Hub Dataset")
    target: str = Field(..., description="The name of the target resource in the Extralit Dataset")


class DatasetMapping(BaseModel):
    fields: list[DatasetMappingItem] = Field(..., min_length=1)
    metadata: list[DatasetMappingItem] | None = []
    suggestions: list[DatasetMappingItem] | None = []
    source_id: str | None = Field(
        None,
        description="Dataset-level source identifier (format: import:{import_id}, dataset:{dataset_id}, hub:{repo_id})",
    )
    target_id: str | None = Field(None, description="Dataset-level target identifier for workflow tracking")

    @property
    def sources(self) -> list[str]:
        fields_sources = [field.source for field in self.fields]
        metadata_sources = [metadata.source for metadata in self.metadata]
        suggestions_sources = [suggestion.source for suggestion in self.suggestions]

        return list(set(fields_sources + metadata_sources + suggestions_sources))


class HubDataset(BaseModel):
    name: str
    subset: str
    split: str
    mapping: DatasetMapping


class HubDatasetExport(BaseModel):
    name: str = Field(..., min_length=1)
    subset: str | None = Field("default", min_length=1)
    split: str | None = Field("train", min_length=1)
    private: bool | None = False
    token: str = Field(..., min_length=1)


class ImportHistoryDataset(BaseModel):
    history_id: UUID = Field(..., description="The ID of the import history to import from")
    mapping: DatasetMapping = Field(..., description="The mapping configuration for the import")


class CompatibleDatasetsRequest(BaseModel):
    column_names: list[str] = Field(..., description="List of column names to match against existing datasets")
    workspace_id: UUID | None = Field(None, description="Filter by workspace_id")
