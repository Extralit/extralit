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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import StreamingResponse

from extralit_server.api.handlers.v1.models import proxy
from extralit_server.errors import BadRequestError
from extralit_server.models import User
from tests.factories import AdminFactory, WorkspaceFactory, WorkspaceUserFactory

if TYPE_CHECKING:
    pass


async def aiter(iterable):
    for item in iterable:
        yield item


@pytest.mark.asyncio
async def test_models_proxy_get_request_streaming_as_owner():
    current_user = User(username="testuser", role="owner")

    with patch("extralit_server.api.handlers.v1.models.client.send") as mock_send:
        mock_response = MagicMock()
        mock_response.aiter_raw = MagicMock(return_value=aiter([b"chunk1", b"chunk2"]))
        mock_send.return_value = mock_response

        request = Request(scope={"type": "http", "method": "GET", "query_string": b"workspace=test-workspace"})
        response = await proxy(request, "test-path", current_user)

        assert response.status_code == 200
        assert isinstance(response, StreamingResponse)
        chunks = [chunk async for chunk in response.body_iterator]
        assert chunks == [b"chunk1", b"chunk2"]


@pytest.mark.asyncio
async def test_models_proxy_post_request_as_admin():
    workspace = await WorkspaceFactory(name="test-workspace")
    user = await AdminFactory()
    await WorkspaceUserFactory(workspace_id=workspace.id, user_id=user.id)

    with patch("extralit_server.api.handlers.v1.models.client.send") as mock_send:
        mock_response = MagicMock()
        mock_response.aiter_raw.return_value = [b"chunk1", b"chunk2"]
        mock_send.return_value = mock_response

        request = Request(scope={"type": "http", "method": "POST", "query_string": b"workspace=test-workspace"})
        request._json = {"key": "value"}
        response = await proxy(request, "test-path", user)

        assert response.status_code == 200
        assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_models_proxy_put_request():
    current_user = User(username="testuser", role="owner")

    with patch("extralit_server.api.handlers.v1.models.client.send") as mock_send:
        mock_response = MagicMock()
        mock_response.aiter_raw.return_value = [b"chunk1", b"chunk2"]
        mock_send.return_value = mock_response

        request = Request(scope={"type": "http", "method": "PUT", "query_string": b"workspace=test-workspace"})
        request._json = {"key": "value"}
        response = await proxy(request, "test-path", current_user)

        assert response.status_code == 200
        assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_models_proxy_delete_request():
    current_user = User(username="testuser", role="owner")

    with patch("extralit_server.api.handlers.v1.models.client.send") as mock_send:
        mock_response = MagicMock()
        mock_response.aiter_raw.return_value = [b"chunk1", b"chunk2"]
        mock_send.return_value = mock_response

        request = Request(scope={"type": "http", "method": "DELETE", "query_string": b"workspace=test-workspace"})
        response = await proxy(request, "test-path", current_user)

        assert response.status_code == 200
        assert isinstance(response, StreamingResponse)


@pytest.mark.asyncio
async def test_models_proxy_missing_workspace_param():
    current_user = User(username="testuser", role="owner")

    request = Request(scope={"type": "http", "method": "GET", "query_string": b""})
    with pytest.raises(BadRequestError) as exc_info:
        await proxy(request, "test-path", current_user)

    assert exc_info.value.HTTP_STATUS == 400
    assert exc_info.value.message == "`workspace` is required in query parameters"
