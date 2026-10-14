from typing import TYPE_CHECKING

from sqlalchemy import select

from extralit_server.models import Workspace

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_or_new_workspace(session: "AsyncSession", workspace_name: str) -> Workspace:
    result = await session.execute(select(Workspace).filter_by(name=workspace_name))
    workspace = result.scalar_one_or_none()
    return workspace or Workspace(name=workspace_name)
