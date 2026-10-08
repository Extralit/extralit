from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import DatasetPolicy, authorize
from extralit_server.api.schemas.v1.projection import WorkspaceProjection
from extralit_server.contexts import projection
from extralit_server.database import get_async_db
from extralit_server.models.database import User
from extralit_server.security import auth

router = APIRouter(tags=["projection"])

LIST_PROJECTION_LIMIT_DEFAULT = 50
LIST_PROJECTION_LIMIT_LE = 100


@router.get("/me/datasets/projection", response_model=WorkspaceProjection)
async def get_workspace_projection(
    *,
    workspace_id: Annotated[UUID, Query(description="The workspace to project")],
    offset: Annotated[int, Query(ge=0, description="Reference offset (not fan-out rows)")] = 0,
    limit: Annotated[int, Query(ge=1, le=LIST_PROJECTION_LIMIT_LE)] = LIST_PROJECTION_LIMIT_DEFAULT,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
):
    await authorize(current_user, DatasetPolicy.list(workspace_id))

    # offset/limit count references, not fan-out rows — a reference with a stacked table
    # question spans several rows and must never be split across a page boundary.
    return await projection.build_workspace_view(db, workspace_id=workspace_id, offset=offset, limit=limit)
