from fastapi import FastAPI

from extralit_server._version import __version__ as extralit_version
from extralit_server.api.errors.v1.exception_handlers import add_exception_handlers as add_exception_handlers_v1
from extralit_server.api.handlers.v1 import authentication as authentication_v1
from extralit_server.api.v2 import annotation as annotation_v2
from extralit_server.api.v2 import questions as questions_v2
from extralit_server.api.v2 import records as records_v2
from extralit_server.api.v2 import schemas as schemas_v2
from extralit_server.errors.base_errors import __ALL__
from extralit_server.errors.error_handler import APIErrorHandler


def create_api_v2() -> FastAPI:
    api_v2 = FastAPI(
        title="Extralit v2",
        description="Extralit Server API v2 (schema-centric)",
        version=str(extralit_version),
        responses={error.HTTP_STATUS: error.api_documentation() for error in __ALL__},
    )
    APIErrorHandler.configure_app(api_v2)
    add_exception_handlers_v1(api_v2)

    # Auth endpoints are reused from v1 so v2 tokens work identically.
    api_v2.include_router(authentication_v1.router)
    api_v2.include_router(schemas_v2.router)
    api_v2.include_router(records_v2.router)
    api_v2.include_router(questions_v2.router)
    api_v2.include_router(annotation_v2.router)
    return api_v2


api_v2 = create_api_v2()
