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

"""
Imporfor processing ta sources into Argilasets.

Thisodule providebackground jobs for data from different sources:
- ImportHistory: Import data from previously uploaded files stored in ImportHistory
- Future: Additional import sources can be added here

The jobs use the same DatasetMapping schema for consistency with existing Hub imports.
"""

"""
Import jobs for processing data from various sources into Extralit datasets.

This module provides background jobs for importing data from ImportHistory records,
reusing the same mapping and processing infrastructure as HuggingFace Hub imports.
"""

from typing import Any
from uuid import UUID

from rq import Retry
from rq.decorators import job
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.schemas.v1.datasets import DatasetMapping
from extralit_server.api.schemas.v1.records import RecordUpsert as RecordUpsertSchema
from extralit_server.api.schemas.v1.records_bulk import RecordsBulkUpsert as RecordsBulkUpsertSchema
from extralit_server.api.schemas.v1.suggestions import SuggestionCreate
from extralit_server.contexts.records_bulk import UpsertRecordsBulk
from extralit_server.database import AsyncSessionLocal
from extralit_server.jobs.queues import DEFAULT_QUEUE, JOB_TIMEOUT_DISABLED, REDIS_CONNECTION
from extralit_server.models import Dataset, ImportHistory
from extralit_server.search_engine.base import SearchEngine
from extralit_server.settings import settings

BATCH_SIZE = 100


class ImportHistoryDataset:
    """Adapter class to process ImportHistory data similar to HubDataset"""

    def __init__(self, import_history: ImportHistory, mapping: DatasetMapping):
        self.import_history = import_history
        self.mapping = mapping
        self.data = import_history.data.get("data", [])
        self.row_idx = -1

    def _next_row_idx(self) -> int:
        self.row_idx += 1
        return self.row_idx

    async def import_to(self, db: AsyncSession, search_engine: SearchEngine, dataset: Dataset) -> None:
        if not dataset.is_ready:
            raise Exception("it's not possible to import records to a non published dataset")

        self.row_idx = -1

        # Process data in batches
        for i in range(0, len(self.data), BATCH_SIZE):
            batch = self.data[i : i + BATCH_SIZE]
            await self._import_batch_to(db, search_engine, batch, dataset)

    async def _import_batch_to(
        self, db: AsyncSession, search_engine: SearchEngine, batch: list[dict[str, Any]], dataset: Dataset
    ) -> None:
        items = []
        for row in batch:
            items.append(self._row_to_record_schema(row, dataset))

        await UpsertRecordsBulk(db, search_engine).upsert_records_bulk(
            dataset,
            RecordsBulkUpsertSchema(items=items),
            raise_on_error=True,
        )

    def _row_to_record_schema(self, row: dict[str, Any], dataset: Dataset) -> RecordUpsertSchema:
        return RecordUpsertSchema(
            id=None,
            external_id=self._row_external_id(row),
            fields=self._row_fields(row, dataset),
            metadata=self._row_metadata(row, dataset),
            suggestions=self._row_suggestions(row, dataset),
            responses=None,
            vectors=None,
        )

    def _row_external_id(self, row: dict[str, Any]) -> str:
        # Try to create a meaningful external_id from metadata fields, typically "reference"
        if row.get("reference"):
            return str(row["reference"])

        # Create composite key from multiple metadata fields if available
        key_parts = []
        for mapping_metadata in self.mapping.metadata or []:
            if row.get(mapping_metadata.source):
                key_parts.append(f"{mapping_metadata.source}_{row[mapping_metadata.source]}")

        if key_parts:
            return "_".join(key_parts)

        # Fallback to sequential ID when no meaningful metadata available
        return f"import_history_{self.import_history.id}_{self._next_row_idx()}"

    def _row_fields(self, row: dict[str, Any], dataset: Dataset) -> dict[str, Any]:
        fields = {}
        for mapping_field in self.mapping.fields:
            value = row.get(mapping_field.source)
            field = dataset.field_by_name(mapping_field.target)
            if value is None or not field:
                continue

            if field.is_text and value is not None:
                value = str(value)

            fields[field.name] = value

        return fields

    def _row_metadata(self, row: dict[str, Any], dataset: Dataset) -> dict[str, Any]:
        metadata = {}
        for mapping_metadata in self.mapping.metadata or []:
            value = row.get(mapping_metadata.source)
            metadata_property = dataset.metadata_property_by_name(mapping_metadata.target)
            if value is None or not metadata_property:
                continue

            metadata[metadata_property.name] = value

        return metadata

    def _row_suggestions(self, row: dict[str, Any], dataset: Dataset) -> list[SuggestionCreate]:
        suggestions = []
        for mapping_suggestion in self.mapping.suggestions or []:
            value = row.get(mapping_suggestion.source)
            question = dataset.question_by_name(mapping_suggestion.target)
            if value is None or not question:
                continue

            if question.is_text or question.is_label_selection:
                value = str(value)

            if question.is_multi_label_selection:
                if isinstance(value, list):
                    value = [str(v) for v in value]
                else:
                    value = [str(value)]

            if question.is_rating:
                value = int(value)  # type: ignore

            suggestions.append(
                SuggestionCreate(
                    question_id=question.id,
                    value=value,
                    type=None,
                    agent=None,
                    score=None,
                ),
            )

        return suggestions


@job(DEFAULT_QUEUE, connection=REDIS_CONNECTION, timeout=JOB_TIMEOUT_DISABLED, retry=Retry(max=3))
async def import_dataset_from_import_history_job(history_id: UUID, dataset_id: UUID, mapping: dict) -> None:
    """
    Import dataset records from ImportHistory data.

    This job loads data from an ImportHistory data and creates dataset records
    using the same mapping containing fields, metadata, and suggestions configured in DatasetConfiguration.

    Args:
        history_id: UUID of the ImportHistory record containing the data
        dataset_id: UUID of the Dataset to import records into
    """
    async with AsyncSessionLocal() as db:
        import_history = await ImportHistory.get_or_raise(db, history_id)

        dataset = await Dataset.get_or_raise(
            db,
            dataset_id,
            options=[
                selectinload(Dataset.fields),
                selectinload(Dataset.questions),
                selectinload(Dataset.metadata_properties),
            ],
        )

        async with SearchEngine.get_by_name(settings.search_engine) as search_engine:
            # Add source_id provenance to the mapping
            mapping_with_provenance = {**mapping}
            mapping_with_provenance["source_id"] = f"import:{history_id}"
            mapping_with_provenance["target_id"] = None  # Set to None for incoming datasets

            parsed_mapping = DatasetMapping.model_validate(mapping_with_provenance)

            # Store the mapping with provenance in dataset metadata for persistence
            dataset.metadata_ = dataset.metadata_ or {}
            dataset.metadata_["mapping"] = parsed_mapping.model_dump()
            await dataset.save(db)

            await ImportHistoryDataset(import_history, parsed_mapping).import_to(db, search_engine, dataset)
