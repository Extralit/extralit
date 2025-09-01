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

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import DatasetPolicy, MetadataPropertyPolicy, authorize, is_authorized
from extralit_server.api.schemas.v1.datasets import (
    CompatibleDatasetsRequest,
    DatasetCreate,
    DatasetMetrics,
    DatasetProgress,
    Datasets,
    DatasetUpdate,
    HubDataset,
    HubDatasetExport,
    ImportHistoryDataset,
    UsersProgress,
)
from extralit_server.api.schemas.v1.datasets import (
    Dataset as DatasetSchema,
)
from extralit_server.api.schemas.v1.fields import Field, FieldCreate, Fields
from extralit_server.api.schemas.v1.jobs import Job as JobSchema
from extralit_server.api.schemas.v1.metadata_properties import (
    MetadataProperties,
    MetadataProperty,
    MetadataPropertyCreate,
)
from extralit_server.api.schemas.v1.vector_settings import VectorSettings, VectorSettingsCreate, VectorsSettings
from extralit_server.contexts import datasets
from extralit_server.database import get_async_db
from extralit_server.enums import DatasetStatus
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.jobs import hub_jobs, import_jobs
from extralit_server.models import Dataset, User
from extralit_server.search_engine import (
    SearchEngine,
    get_search_engine,
)
from extralit_server.security import auth

router = APIRouter()


async def _filter_metadata_properties_by_policy(
    current_user: User, metadata_properties: list[MetadataProperty]
) -> list[MetadataProperty]:
    filtered_metadata_properties = []

    for metadata_property in metadata_properties:
        metadata_property_is_authorized = await is_authorized(
            current_user, MetadataPropertyPolicy.get(metadata_property)
        )

        if metadata_property_is_authorized:
            filtered_metadata_properties.append(metadata_property)

    return filtered_metadata_properties


@router.get("/me/datasets", response_model=Datasets)
async def list_current_user_datasets(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID | None, Query(description="Filter by workspace_id")] = None,
    name: Annotated[str | None, Query(description="Filter by dataset name")] = None,
    status: Annotated[DatasetStatus | None, Query(description="Filter by dataset status")] = None,
):
    await authorize(current_user, DatasetPolicy.list(workspace_id))

    filters = {
        "workspace_id": workspace_id,
        "name": name,
        "status": status,
    }

    dataset_list = await datasets.list_datasets(
        db, user=current_user, **{k: v for k, v in filters.items() if v is not None}
    )

    return Datasets(items=dataset_list)


@router.post("/datasets/compatible", response_model=Datasets)
async def list_compatible_datasets(
    *,
    request: CompatibleDatasetsRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, DatasetPolicy.list(request.workspace_id))

    filters = {
        "workspace_id": request.workspace_id,
        "status": DatasetStatus.ready,
    }

    dataset_list = await datasets.list_datasets(
        db, user=current_user, **{k: v for k, v in filters.items() if v is not None}
    )

    all_datasets = Datasets(items=dataset_list)

    return all_datasets.get_compatible_datasets(request.column_names)


@router.get("/datasets/{dataset_id}/fields", response_model=Fields)
async def list_dataset_fields(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id, options=[selectinload(Dataset.fields)])

    await authorize(current_user, DatasetPolicy.get(dataset))

    return Fields(items=dataset.fields)


@router.get("/datasets/{dataset_id}/vectors-settings", response_model=VectorsSettings)
async def list_dataset_vector_settings(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id, options=[selectinload(Dataset.vectors_settings)])

    await authorize(current_user, DatasetPolicy.get(dataset))

    return VectorsSettings(items=dataset.vectors_settings)


@router.get("/me/datasets/{dataset_id}/metadata-properties", response_model=MetadataProperties)
async def list_current_user_dataset_metadata_properties(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id, options=[selectinload(Dataset.metadata_properties)])

    await authorize(current_user, DatasetPolicy.get(dataset))

    filtered_metadata_properties = await _filter_metadata_properties_by_policy(
        current_user, dataset.metadata_properties
    )

    return MetadataProperties(items=filtered_metadata_properties)


@router.get("/datasets/{dataset_id}", response_model=DatasetSchema)
async def get_dataset(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.get(dataset))

    return dataset


@router.get("/me/datasets/{dataset_id}/metrics", response_model=DatasetMetrics)
async def get_current_user_dataset_metrics(
    *,
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.get(dataset))

    result = await datasets.get_user_dataset_metrics(db, search_engine, current_user, dataset)

    return DatasetMetrics(responses=result)


@router.get("/datasets/{dataset_id}/progress", response_model=DatasetProgress, response_model_exclude_unset=True)
async def get_dataset_progress(
    *,
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.get(dataset))

    result = await datasets.get_dataset_progress(db, search_engine, dataset)

    return DatasetProgress(**result)


@router.get("/datasets/{dataset_id}/users/progress", response_model=UsersProgress)
async def get_dataset_users_progress(
    *,
    dataset_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.get(dataset))

    progress = await datasets.get_dataset_users_progress(db, dataset)

    return UsersProgress(users=progress)


@router.post("/datasets", status_code=status.HTTP_201_CREATED, response_model=DatasetSchema)
async def create_dataset(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_create: DatasetCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, DatasetPolicy.create(dataset_create.workspace_id))

    return await datasets.create_dataset(db, dataset_create.model_dump())


@router.post("/datasets/{dataset_id}/fields", status_code=status.HTTP_201_CREATED, response_model=Field)
async def create_dataset_field(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    field_create: FieldCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.create_field(dataset))

    return await datasets.create_field(db, dataset, field_create)


@router.post(
    "/datasets/{dataset_id}/metadata-properties", status_code=status.HTTP_201_CREATED, response_model=MetadataProperty
)
async def create_dataset_metadata_property(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    dataset_id: UUID,
    metadata_property_create: MetadataPropertyCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.create_metadata_property(dataset))

    return await datasets.create_metadata_property(db, search_engine, dataset, metadata_property_create)


@router.post(
    "/datasets/{dataset_id}/vectors-settings", status_code=status.HTTP_201_CREATED, response_model=VectorSettings
)
async def create_dataset_vector_settings(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    dataset_id: UUID,
    vector_settings_create: VectorSettingsCreate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.create_vector_settings(dataset))

    return await datasets.create_vector_settings(db, search_engine, dataset, vector_settings_create)


@router.put("/datasets/{dataset_id}/publish", response_model=DatasetSchema)
async def publish_dataset(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
) -> Dataset:
    dataset = await Dataset.get_or_raise(
        db,
        dataset_id,
        options=[
            selectinload(Dataset.fields),
            selectinload(Dataset.questions),
            selectinload(Dataset.metadata_properties),
            selectinload(Dataset.vectors_settings),
        ],
    )

    await authorize(current_user, DatasetPolicy.publish(dataset))

    dataset = await datasets.publish_dataset(db, search_engine, dataset)

    return dataset


@router.delete("/datasets/{dataset_id}", response_model=DatasetSchema)
async def delete_dataset(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    dataset_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.delete(dataset))

    return await datasets.delete_dataset(db, search_engine, dataset)


@router.patch("/datasets/{dataset_id}", response_model=DatasetSchema)
async def update_dataset(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    dataset_update: DatasetUpdate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.update(dataset))

    return await datasets.update_dataset(db, dataset, dataset_update.model_dump(exclude_unset=True))


@router.post("/datasets/{dataset_id}/import-hub", status_code=status.HTTP_202_ACCEPTED, response_model=JobSchema)
async def import_dataset_from_hub(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    hub_dataset: HubDataset,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.import_from_hub(dataset))

    job = hub_jobs.import_dataset_from_hub_job.delay(
        name=hub_dataset.name,
        subset=hub_dataset.subset,
        split=hub_dataset.split,
        dataset_id=dataset.id,
        mapping=hub_dataset.mapping.model_dump(),
    )

    return JobSchema(id=job.id, status=job.get_status())


@router.post("/datasets/{dataset_id}/import", status_code=status.HTTP_202_ACCEPTED, response_model=JobSchema)
async def import_dataset_from_import_history(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    import_history_dataset: ImportHistoryDataset,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.import_from_hub(dataset))

    job = import_jobs.import_dataset_from_import_history_job.delay(
        history_id=import_history_dataset.history_id,
        dataset_id=dataset.id,
        mapping=import_history_dataset.mapping.model_dump(),
    )

    return JobSchema(id=job.id, status=job.get_status())


@router.post("/datasets/{dataset_id}/export", status_code=status.HTTP_202_ACCEPTED, response_model=JobSchema)
async def export_dataset_to_hub(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    dataset_id: UUID,
    hub_dataset: HubDatasetExport,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    dataset = await Dataset.get_or_raise(db, dataset_id)

    await authorize(current_user, DatasetPolicy.export_to_hub(dataset))

    if not await datasets.dataset_has_records(db, dataset):
        raise UnprocessableEntityError(f"Dataset with id `{dataset.id}` has no records to export")

    job = hub_jobs.export_dataset_to_hub_job.delay(
        name=hub_dataset.name,
        subset=hub_dataset.subset,
        split=hub_dataset.split,
        private=hub_dataset.private,
        token=hub_dataset.token,
        dataset_id=dataset.id,
    )

    return JobSchema(id=job.id, status=job.get_status())
