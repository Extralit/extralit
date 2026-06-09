from typing import Annotated

from fastapi import APIRouter, Depends

from extralit_server.api.schemas.v1.info import Status, Version
from extralit_server.contexts import info
from extralit_server.search_engine import SearchEngine, get_search_engine

router = APIRouter(tags=["info"])


@router.get("/version", response_model=Version)
async def get_version():
    return Version(version=info.extralit_version())


@router.get("/status", response_model=Status)
async def get_status(search_engine: Annotated[SearchEngine, Depends(get_search_engine)]):
    return Status(
        version=info.extralit_version(),
        search_engine=await search_engine.info(),
        memory=info.memory_status(),
    )
