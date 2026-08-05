from fastapi import APIRouter

from extralit_server.api.handlers.v1.datasets.datasets import router as datasets_router
from extralit_server.api.handlers.v1.datasets.questions import router as questions_router
from extralit_server.api.handlers.v1.datasets.records import router as records_router
from extralit_server.api.handlers.v1.datasets.records_bulk import router as records_bulk_router
from extralit_server.api.handlers.v1.datasets.schema_versions import router as schema_versions_router

router = APIRouter(tags=["datasets"])

router.include_router(datasets_router)
router.include_router(questions_router)
router.include_router(records_router)
router.include_router(records_bulk_router)
router.include_router(schema_versions_router)
