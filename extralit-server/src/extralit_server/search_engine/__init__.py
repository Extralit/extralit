from collections.abc import AsyncGenerator

from ..settings import settings
from .base import *
from .base import SearchEngine
from .elasticsearch import ElasticSearchEngine
from .opensearch import OpenSearchEngine


async def get_search_engine() -> AsyncGenerator[SearchEngine, None]:
    async with SearchEngine.get_by_name(settings.search_engine) as engine:
        yield engine
