from fastapi import APIRouter

from extralit_server.api.schemas.v1.settings import Settings
from extralit_server.contexts import settings

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=Settings, response_model_exclude_none=True)
async def get_settings():
    return settings.get_settings()
