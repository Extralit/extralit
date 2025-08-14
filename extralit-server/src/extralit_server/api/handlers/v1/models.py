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

import logging
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.responses import StreamingResponse

from extralit_server.errors import BadRequestError, UnauthorizedError
from extralit_server.models import User
from extralit_server.security import auth
from extralit_server.settings import settings

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["models"])

client = httpx.AsyncClient(timeout=10.0)


@router.api_route(
    "/models/{rest_of_path:path}", methods=["GET", "POST", "PUT", "DELETE"], response_class=StreamingResponse
)
async def proxy(request: Request, rest_of_path: str, current_user: User = Depends(auth.get_current_user)):
    url = urljoin(settings.extralit_url, rest_of_path)
    params = dict(request.query_params)

    _LOGGER.info("PROXY %s %s", url, params)

    if "workspace" not in params or not params["workspace"]:
        raise BadRequestError("`workspace` is required in query parameters")

    if current_user:
        params["username"] = current_user.username

        if current_user.role != "owner" and not await current_user.is_member_of_workspace_name(params["workspace"]):
            raise UnauthorizedError(
                f"{current_user.username} is not authorized to access workspace {params['workspace']}"
            )

    if request.method == "GET":
        proxy_request = client.build_request("GET", url, params=params)
    elif request.method == "POST":
        data = await request.json()
        proxy_request = client.build_request("POST", url, json=data, params=params)
    elif request.method == "PUT":
        data = await request.json()
        proxy_request = client.build_request("PUT", url, data=data, params=params)
    elif request.method == "DELETE":
        proxy_request = client.build_request("DELETE", url, params=params)
    else:
        return {"message": "Method not supported"}

    async def stream_response():
        try:
            response = await client.send(proxy_request, stream=True)
            async for chunk in response.aiter_raw():
                yield chunk
        except httpx.ReadTimeout as exc:
            _LOGGER.error("Request to %s timed out.", exc.request.url)
            yield b"Request timed out."
        except httpx.TimeoutException as exc:
            _LOGGER.error("Request to %s timed out.", exc.request.url)
            yield b"Request timed out."
        except httpx.RequestError as exc:
            _LOGGER.error("An error occurred while requesting %s: %s", exc.request.url, exc)
            yield b"An error occurred while processing the request."

    return StreamingResponse(stream_response(), media_type="text/event-stream")


@router.on_event("startup")
async def startup_event():
    global client
    if client is None:
        client = httpx.AsyncClient(timeout=10.0)


@router.on_event("shutdown")
async def shutdown():
    await client.aclose()
