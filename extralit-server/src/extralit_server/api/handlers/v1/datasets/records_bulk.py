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

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from extralit_server.api.policies.v1 import DatasetPolicy, authorize
from extralit_server.api.schemas.v1.records_bulk import RecordsBulk, RecordsBulkCreate, RecordsBulkUpsert
from extralit_server.contexts.records_bulk import CreateRecordsBulk, UpsertRecordsBulk
from extralit_server.database import get_async_db
from extralit_server.models import Dataset, User
from extralit_server.search_engine import SearchEngine, get_search_engine
from extralit_server.security import auth

router = APIRouter()


@router.post(
    "/datasets/{dataset_id}/records/bulk",
    response_model=RecordsBulk,
    status_code=status.HTTP_201_CREATED,
)
async def create_dataset_records_bulk(
    *,
    dataset_id: UUID,
    records_bulk_create: RecordsBulkCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
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

    await authorize(current_user, DatasetPolicy.create_records(dataset))

    return await CreateRecordsBulk(db, search_engine).create_records_bulk(dataset, records_bulk_create)


@router.put("/datasets/{dataset_id}/records/bulk", response_model=RecordsBulk)
async def upsert_dataset_records_bulk(
    *,
    dataset_id: UUID,
    records_bulk_upsert: RecordsBulkUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
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

    await authorize(current_user, DatasetPolicy.upsert_records(dataset))

    return await UpsertRecordsBulk(db, search_engine).upsert_records_bulk(dataset, records_bulk_upsert)
