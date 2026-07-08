from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from extralit_server.api.policies.v1 import V2SuggestionPolicy, authorize
from extralit_server.api.schemas.v2.annotation import SuggestionRead, Suggestions, SuggestionUpsert
from extralit_server.contexts.v2 import annotation as annotation_ctx
from extralit_server.database import get_async_db
from extralit_server.errors.future import NotFoundError, UnprocessableEntityError
from extralit_server.models import User
from extralit_server.models.v2 import V2Record
from extralit_server.security import auth

router = APIRouter(tags=["v2: annotation"])


async def _get_record_or_404(db: AsyncSession, record_id: UUID) -> V2Record:
    # `schema` is eager-loaded here (rather than lazily accessed) because the suggestion
    # policies read `record.schema.workspace_id` synchronously, which AsyncSession cannot
    # lazy-load outside an active greenlet.
    record = await V2Record.get(db, record_id, options=[selectinload(V2Record.schema)])
    if record is None:
        raise NotFoundError(f"Record with id `{record_id}` not found")
    return record


@router.put("/records/{record_id}/suggestions", response_model=SuggestionRead)
async def upsert_suggestion(
    *,
    record_id: UUID,
    payload: SuggestionUpsert,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2SuggestionPolicy.write(record))
    question = await annotation_ctx.get_question(db, payload.question_id)
    if question is None or question.schema_id != record.schema_id:
        raise UnprocessableEntityError(f"question `{payload.question_id}` does not belong to this record's schema")
    return await annotation_ctx.upsert_suggestion(db, record, question, upsert=payload)


@router.get("/records/{record_id}/suggestions", response_model=Suggestions)
async def list_suggestions(
    *,
    record_id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    record = await _get_record_or_404(db, record_id)
    await authorize(current_user, V2SuggestionPolicy.read(record))
    return Suggestions(items=await annotation_ctx.list_suggestions(db, record))
