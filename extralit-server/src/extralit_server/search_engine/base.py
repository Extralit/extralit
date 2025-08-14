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
import dataclasses
from abc import ABCMeta, abstractmethod
from collections.abc import AsyncGenerator, Iterable
from contextlib import asynccontextmanager
from typing import (
    Generic,
    Literal,
    TypeVar,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from extralit_server.enums import (
    MetadataPropertyType,
    RecordSortField,
    ResponseStatus,
    ResponseStatusFilter,
    SimilarityOrder,
    SortOrder,
)
from extralit_server.models import Dataset, MetadataProperty, Record, Response, Suggestion, User, VectorSettings

__all__ = [
    "AndFilter",
    "Filter",
    "FilterScope",
    "FloatMetadataMetrics",
    "IntegerMetadataMetrics",
    "MetadataFilterScope",
    "MetadataMetrics",
    "Order",
    "RangeFilter",
    "RecordFilterScope",
    "ResponseFilterScope",
    "SearchEngine",
    "SearchResponseItem",
    "SearchResponses",
    "SortBy",
    "SuggestionFilterScope",
    "TermsFilter",
    "TermsMetrics",
    "TextQuery",
    "UserResponseStatusFilter",
]


@dataclasses.dataclass
class SuggestionFilterScope:
    question: str
    property: str


@dataclasses.dataclass
class ResponseFilterScope:
    question: str | None = None
    property: str | None = None
    user: User | None = None


@dataclasses.dataclass
class MetadataFilterScope:
    metadata_property: str


@dataclasses.dataclass
class RecordFilterScope:
    property: str


FilterScope = Union[SuggestionFilterScope, ResponseFilterScope, MetadataFilterScope, RecordFilterScope]


@dataclasses.dataclass
class TermsFilter:
    scope: FilterScope
    values: list[str]


@dataclasses.dataclass
class RangeFilter:
    scope: FilterScope
    ge: float | None = None
    le: float | None = None


@dataclasses.dataclass
class AndFilter:
    filters: list["Filter"]


Filter = Union[AndFilter, TermsFilter, RangeFilter]


@dataclasses.dataclass
class Order:
    scope: FilterScope
    order: SortOrder


class TextQuery(BaseModel):
    q: str
    field: str | None = None

    model_config = ConfigDict(coerce_numbers_to_str=True)


class UserResponseStatusFilter(BaseModel):
    statuses: list[ResponseStatusFilter]
    user: User | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def response_statuses(self) -> list[ResponseStatus]:
        return [status.value for status in self.statuses if status == ResponseStatusFilter.pending]


class SearchResponseItem(BaseModel):
    record_id: UUID
    score: float | None = None


class SearchResponses(BaseModel):
    items: list[SearchResponseItem]
    total: int = 0


class SortBy(BaseModel):
    field: MetadataProperty | RecordSortField
    order: SortOrder = SortOrder.asc

    class Config:
        arbitrary_types_allowed = True


class TermsMetrics(BaseModel):
    class TermCount(BaseModel):
        term: str
        count: int

    type: Literal["terms"] = "terms"
    total: int
    values: list[TermCount] = Field(default_factory=list)


NT = TypeVar("NT", int, float)


class NumericMetadataMetrics(BaseModel, Generic[NT]):
    min: NT | None = None
    max: NT | None = None


class IntegerMetadataMetrics(NumericMetadataMetrics[int]):
    type: MetadataPropertyType = Field(MetadataPropertyType.integer)


class FloatMetadataMetrics(NumericMetadataMetrics[float]):
    type: MetadataPropertyType = Field(MetadataPropertyType.float)


MetadataMetrics = Union[TermsMetrics, IntegerMetadataMetrics, FloatMetadataMetrics]


class SearchEngine(metaclass=ABCMeta):
    registered_classes = {}

    @classmethod
    @abstractmethod
    async def new_instance(cls) -> "SearchEngine":
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def ping(self) -> bool:
        pass

    @abstractmethod
    async def info(self) -> dict:
        pass

    @classmethod
    def register(cls, engine_name: str):
        def decorator(engine_class):
            cls.registered_classes[engine_name] = engine_class
            return engine_class

        return decorator

    @classmethod
    @asynccontextmanager
    async def get_by_name(cls, engine_name: str) -> AsyncGenerator["SearchEngine", None]:
        engine_name = engine_name.lower().strip()

        if engine_name not in cls.registered_classes:
            raise ValueError(f"No engine class registered for '{engine_name}'")

        engine_class = cls.registered_classes[engine_name]

        engine = None

        try:
            engine = await engine_class.new_instance()
            yield engine
        except Exception as e:
            raise e
        finally:
            if engine is not None:
                await engine.close()

    @abstractmethod
    async def get_all_index_names(self) -> list[str]:
        pass

    @abstractmethod
    async def create_index(self, dataset: Dataset):
        pass

    @abstractmethod
    async def delete_index(self, dataset: Dataset):
        pass

    @abstractmethod
    async def configure_metadata_property(self, dataset: Dataset, metadata_property: MetadataProperty):
        pass

    @abstractmethod
    async def index_records(self, dataset: Dataset, records: Iterable[Record]):
        pass

    @abstractmethod
    async def partial_record_update(self, record: Record, **update):
        pass

    @abstractmethod
    async def delete_records(self, dataset: Dataset, records: Iterable[Record]):
        pass

    @abstractmethod
    async def update_record_response(self, response: Response):
        pass

    @abstractmethod
    async def delete_record_response(self, response: Response):
        pass

    @abstractmethod
    async def update_record_suggestion(self, suggestion: Suggestion):
        pass

    @abstractmethod
    async def delete_record_suggestion(self, suggestion: Suggestion):
        pass

    @abstractmethod
    async def get_dataset_progress(self, dataset: Dataset) -> dict:
        pass

    @abstractmethod
    async def get_dataset_user_progress(self, dataset: Dataset, user: User) -> dict:
        pass

    @abstractmethod
    async def search(
        self,
        dataset: Dataset,
        query: TextQuery | str | None = None,
        filter: Filter | None = None,
        sort: list[Order] | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> SearchResponses:
        pass

    @abstractmethod
    async def compute_metrics_for(self, metadata_property: MetadataProperty) -> MetadataMetrics:
        pass

    async def configure_index_vectors(self, vector_settings: VectorSettings):
        pass

    @abstractmethod
    async def similarity_search(
        self,
        dataset: Dataset,
        vector_settings: VectorSettings,
        value: list[float] | None = None,
        record: Record | None = None,
        query: TextQuery | str | None = None,
        filter: Filter | None = None,
        max_results: int = 100,
        order: SimilarityOrder = SimilarityOrder.most_similar,
        threshold: float | None = None,
    ) -> SearchResponses:
        pass
