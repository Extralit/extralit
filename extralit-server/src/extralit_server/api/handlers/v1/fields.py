from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import FieldPolicy, authorize
from extralit_server.api.schemas.v1.fields import Field as FieldSchema
from extralit_server.api.schemas.v1.fields import FieldUpdate
from extralit_server.contexts import datasets
from extralit_server.database import get_async_db
from extralit_server.models import Field, User
from extralit_server.security import auth

router = APIRouter(tags=["fields"])


@router.patch("/fields/{field_id}", response_model=FieldSchema)
async def update_field(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    field_id: UUID,
    field_update: FieldUpdate,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    field = await Field.get_or_raise(db, field_id, options=[selectinload(Field.dataset)])

    await authorize(current_user, FieldPolicy.update(field))

    return await datasets.update_field(db, field, field_update)


@router.delete("/fields/{field_id}", response_model=FieldSchema)
async def delete_field(
    *,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    field_id: UUID,
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    field = await Field.get_or_raise(db, field_id, options=[selectinload(Field.dataset)])

    await authorize(current_user, FieldPolicy.delete(field))

    return await datasets.delete_field(db, field)
