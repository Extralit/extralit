# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import glob
import inspect
import logging
import os
import shutil
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

import backoff
import redis
from brotli_asgi import BrotliMiddleware
from fastapi import FastAPI, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import URL
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse, RedirectResponse

from extralit_server import helpers
from extralit_server._version import __version__ as extralit_version
from extralit_server.api.routes import api_v1
from extralit_server.constants import DEFAULT_API_KEY, DEFAULT_PASSWORD, DEFAULT_USERNAME
from extralit_server.contexts import accounts, files
from extralit_server.database import get_async_db
from extralit_server.jobs.queues import REDIS_CONNECTION
from extralit_server.logging import configure_logging
from extralit_server.models import User, Workspace
from extralit_server.search_engine import get_search_engine
from extralit_server.settings import settings
from extralit_server.static_rewrite import RewriteStaticFiles
from extralit_server.telemetry import get_telemetry_client

_LOGGER = logging.getLogger("extralit")


@contextlib.asynccontextmanager
async def app_lifespan(app: FastAPI):
    # See https://fastapi.tiangolo.com/advanced/events/#lifespan
    await configure_database()
    await configure_search_engine()
    configure_redis()
    track_server_startup()

    yield


def configure_share_your_progress(app: FastAPI):
    if settings.enable_share_your_progress is False:
        return

    def create_image_link(username: str, dataset_name: str, submitted: int, team_progress: float) -> str:
        url = "https://argilla.imglab-cdn.net/dibt/dibt_v2.png"

        text = f"""<span size="9pt" weight="bold">@{username}</span>
I've just contributed <span weight="bold">{submitted}</span> examples to this dataset:
<span size="9pt" weight="bold">{dataset_name}</span>

<span size="8pt">Team progress</span>
<span weight="bold">{team_progress}%</span>"""

        params = {
            "width": "1200",
            "text": text,
            "text-width": "700",
            "text-height": "590",
            "text-padding": "60",
            "text-color": "39,71,111",
            "text-x": "460",
            "text-y": "40",
            "format": "png",
            "dpr": "2",
        }

        return f"{url}?{urlencode(params)}"

    def create_share_html(dataset_name: str, dataset_id: str, share_image: str, url: URL) -> str:
        share_page = f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title{dataset_name}</title>

                <meta property="og:title" content="{dataset_name}" />
                <meta
                  property="og:description"
                  content="Join and contribute to the dataset {dataset_name}"
                />
                <meta property="og:type" content="website" />
                <meta property="og:url" content="{url}" />
                <meta property="og:image" content="{share_image}" />
                <meta property="og:site_name" content="Extralit" />
                <meta property="og:locale" content="en_US" />

                <!-- Twitter meta tags -->
                <meta name="twitter:card" content="summary_large_image" />
                <meta name="twitter:title" content="{dataset_name}" />
                <meta
                  name="twitter:description"
                  content="Join and contribute to the dataset {dataset_name}"
                />
                <meta name="twitter:image" content="{share_image}" />
                <meta name="twitter:site" content="{url}" />
              </head>
              <body>
                <script>
                  window.location.href = `${{window.location.origin}}/dataset/{dataset_id}/annotation-mode`;
                </script>
              </body>
            </html>
        """

        return textwrap.dedent(share_page)

    @app.get("/share-your-progress", include_in_schema=False)
    async def share_your_progress_page(
        request: Request,
        dataset_name: Annotated[str, Query()],
        dataset_id: Annotated[str, Query()],
        user_name: Annotated[str, Query()],
        team_progress: Annotated[float, Query()] = 0.0,
        records_submitted: Annotated[int, Query()] = 0,
    ):
        share_image = create_image_link(user_name, dataset_name, records_submitted, team_progress)
        share_page = create_share_html(dataset_name, dataset_id, share_image, request.url)

        return HTMLResponse(content=share_page, status_code=200)


def create_server_app() -> FastAPI:
    """Configure the extralit server"""

    app = FastAPI(
        title="Extralit",
        description="Extralit API",
        docs_url=None,
        redoc_url=None,
        redirect_slashes=False,
        version=str(extralit_version),
        lifespan=app_lifespan,
    )

    configure_logging()
    configure_common_middleware(app)
    configure_api_router(app)
    configure_share_your_progress(app)
    configure_telemetry(app)
    configure_app_statics(app)
    configure_api_docs(app)

    # This if-else clause is needed to simplify the test dependency setup. Otherwise, we cannot override dependencies
    # easily. We can review this once we have separate fastapi application for the api and the webapp.
    if settings.base_url and settings.base_url != "/":
        _app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=True)
        _app.mount(settings.base_url, app)
        return _app
    else:
        return app


def configure_api_docs(app: FastAPI):
    @app.get("/docs", include_in_schema=False)
    async def redirect_docs():
        return RedirectResponse(url=f"{settings.base_url}api/v1/docs")

    @app.get("/api", include_in_schema=False)
    async def redirect_api():
        return RedirectResponse(url=f"{settings.base_url}api/v1/docs")


def configure_common_middleware(app: FastAPI):
    """Configures fastapi middleware"""

    @app.middleware("http")
    async def add_server_timing_header(request: Request, call_next):
        start_time = datetime.utcnow()
        response = await call_next(request)
        response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

        response.headers["Server-Timing"] = f"total;dur={response_time_ms}"

        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(BrotliMiddleware, minimum_size=512, quality=7)


def configure_api_router(app: FastAPI):
    """Configures and set the api router to app"""
    app.mount("/api/v1", api_v1)


def configure_telemetry(app: FastAPI):
    """
    Configures telemetry middleware for the app if telemetry is enabled
    """
    if not settings.enable_telemetry:
        return

    @app.middleware("http")
    async def track_api_requests(request: Request, call_next):
        response = await call_next(request)
        try:
            await get_telemetry_client().track_api_request(request, response)
        except Exception as e:
            _LOGGER.warning(f"Error tracking request: {e}")
        return response


def configure_app_statics(app: FastAPI):
    """Configure static folder for app"""

    parent_path = Path(__file__).parent.absolute()
    statics_folder = Path(os.path.join(parent_path, "static"))
    if not (statics_folder.exists() and statics_folder.is_dir()):
        return

    def _create_statics_folder(path_from):
        """
        Application statics will be created with a parameterized baseUrl variable.

        This function will replace the variable by the real runtime value found in settings.base_url

        This allow us to deploy the extralit server under a custom base url, even when webapp does not
        support it.

        """
        BASE_URL_VAR_NAME = "@@baseUrl@@"
        temp_dir = tempfile.mkdtemp()
        new_folder = shutil.copytree(path_from, temp_dir + "/statics")
        base_url = helpers.remove_suffix(settings.base_url or "", suffix="/")
        for extension in ["*.js", "*.html"]:
            for file in glob.glob(
                f"{new_folder}/**/{extension}",
                recursive=True,
            ):
                helpers.replace_string_in_file(
                    file,
                    string=BASE_URL_VAR_NAME,
                    replace_by=base_url,
                )

        return new_folder

    temp_statics = _create_statics_folder(statics_folder)

    app.mount(
        "/",
        RewriteStaticFiles(directory=temp_statics, html=True, check_dir=False),
        name="static",
    )


def track_server_startup() -> None:
    """
    Track server startup telemetry event if telemetry is enabled
    """
    if not settings.enable_telemetry:
        return

    _show_telemetry_warning()
    get_telemetry_client().track_server_startup()


def _show_telemetry_warning():
    message = "\n"
    message += inspect.cleandoc(
        "Extralit uses telemetry to report anonymous usage and error information. You\n"
        "can know more about what information is reported at:\n\n"
        "    https://docs.extralit.ai/latest/reference/extralit-server/telemetry/\n\n"
        "Telemetry is currently enabled. If you want to disable it, you can configure\n"
        "the environment variable before relaunching the server:\n\n"
        f"{'#set HF_HUB_DISABLE_TELEMETRY=1' if os.name == 'nt' else '$>export HF_HUB_DISABLE_TELEMETRY=1'}"
    )
    _LOGGER.warning(message)


async def _create_oauth_allowed_workspaces(db: AsyncSession):
    from extralit_server.security.settings import settings as security_settings

    for allowed_workspace in security_settings.oauth.allowed_workspaces:
        if await Workspace.get_by(db, name=allowed_workspace.name) is None:
            _LOGGER.info(f"Creating workspace with name {allowed_workspace.name!r}")
            try:
                files.create_bucket(files.get_minio_client(), allowed_workspace.name)
            except Exception as e:
                _LOGGER.error(f"Failed to create bucket for workspace {allowed_workspace.name!r}: {e}")

            await accounts.create_workspace(db, {"name": allowed_workspace.name})


async def _show_default_user_warning(db: AsyncSession):
    def _user_has_default_credentials(user: User):
        return user.api_key == DEFAULT_API_KEY or accounts.verify_password(DEFAULT_PASSWORD, user.password_hash)

    default_user = await User.get_by(db, username=DEFAULT_USERNAME)
    if default_user and _user_has_default_credentials(default_user):
        _LOGGER.warning(
            f"User {DEFAULT_USERNAME!r} with default credentials has been found in the database. "
            "If you are using extralit in a production environment this can be a serious security problem. "
            f"We recommend that you create a new admin user and then delete the default {DEFAULT_USERNAME!r} one."
        )


async def configure_database():
    async with contextlib.asynccontextmanager(get_async_db)() as db:
        await _show_default_user_warning(db)
        await _create_oauth_allowed_workspaces(db)
        try:
            await db.execute(text("SELECT 1"))
        except Exception as e:
            _LOGGER.error(f"Database connection test failed at startup: {e}")
            raise


async def configure_search_engine():
    if settings.search_engine_is_elasticsearch:
        # TODO: Move this to the search engine implementation module
        logging.getLogger("elasticsearch").setLevel(logging.ERROR)
        logging.getLogger("elastic_transport").setLevel(logging.ERROR)

    elif settings.search_engine_is_opensearch:
        # TODO: Move this to the search engine implementation module
        logging.getLogger("opensearch").setLevel(logging.ERROR)
        logging.getLogger("opensearch_transport").setLevel(logging.ERROR)

    @backoff.on_exception(backoff.expo, ConnectionError, max_time=60)
    async def ping_search_engine():
        async for search_engine in get_search_engine():
            if not await search_engine.ping():
                raise ConnectionError(
                    f"Your {settings.search_engine} is not available or not responding.\n"
                    f"Please make sure your {settings.search_engine} instance is launched and correctly running and\n"
                    "you have the necessary access permissions. Once you have verified this, restart "
                    "the extralit server.\n"
                )

    await ping_search_engine()


def configure_redis():
    @backoff.on_exception(backoff.expo, ConnectionError, max_time=60)
    def ping_redis():
        try:
            REDIS_CONNECTION.ping()
        except redis.ConnectionError:
            raise ConnectionError(
                f"Your redis instance at {settings.redis_url} is not available or not responding.\n"
                "Please make sure your redis instance is launched and correctly running and\n"
                "you have the necessary access permissions. Once you have verified this, restart "
                "the extralit server.\n"
            )

    ping_redis()


app = create_server_app()
