from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.policies.v1 import SchemaPolicy, authorize
from extralit_server.api.schemas.v2.projection import ProjectionView
from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.database import get_async_db
from extralit_server.models import User
from extralit_server.security import auth

router = APIRouter(tags=["v2: projection"])


# Distinct `/projection/...` prefix, NOT `/references/{reference:path}/view`: the greedy `:path`
# converter on the existing GET /references/{reference:path} (Phase 3) would otherwise shadow a
# `/view` suffix, and a real reference ending in "/view" would collide. See spec §17.4.
@router.get("/projection/references/{reference:path}", response_model=ProjectionView)
async def get_reference_projection(
    *,
    reference: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[User, Security(auth.get_current_user)],
    workspace_id: Annotated[UUID, Query(description="Workspace to scope the view (required)")],
):
    await authorize(current_user, SchemaPolicy.list(workspace_id))
    return await projection_ctx.build_reference_view(
        db, workspace_id=workspace_id, reference=reference, user=current_user
    )
