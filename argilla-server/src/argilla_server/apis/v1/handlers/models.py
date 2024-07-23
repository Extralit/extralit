import logging
from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse

from argilla_server.models import User
from argilla_server.policies import _exists_workspace_user_by_user_and_workspace_name
from argilla_server.security import auth
from argilla_server.settings import settings

_LOGGER = logging.getLogger("models")

router = APIRouter(tags=["models"])

@router.api_route("/models/{rest_of_path:path}", 
                  methods=["GET", "POST", "PUT", "DELETE"], 
                  response_class=StreamingResponse)
async def proxy(request: Request, rest_of_path: str,
                current_user: User = Depends(auth.get_current_user)):
    url = urljoin(settings.extralit_url, rest_of_path)
    params = dict(request.query_params)

    _LOGGER.info(f'PROXY {url} {params}, {current_user}')

    if 'workspace' not in params or not params['workspace']:
        raise HTTPException(status_code=500, detail="`workspace` is required in query parameters")

    if current_user:
        params['username'] = current_user.username

        if current_user.role != "owner":
            if not await _exists_workspace_user_by_user_and_workspace_name(current_user, params['workspace']):
                raise HTTPException(status_code=500,
                                    detail=f"{current_user.username} is not authorized to access workspace {params['workspace']}")

    client = httpx.AsyncClient(timeout=10.0)
    if request.method == "GET":
        request = client.build_request("GET", url, params=params)
    elif request.method == "POST":
        data = await request.json()
        request = client.build_request("POST", url, json=data, params=params)
    elif request.method == "PUT":
        data = await request.json()
        request = client.build_request("PUT", url, data=data, params=params)
    elif request.method == "DELETE":
        request = client.build_request("DELETE", url, params=params)
    else:
        return {"message": "Method not supported"}

    async def stream_response():
        response = await client.send(request, stream=True)
        async for chunk in response.aiter_raw():
            yield chunk
        await client.aclose()

    return StreamingResponse(stream_response(), media_type="text/event-stream")
    