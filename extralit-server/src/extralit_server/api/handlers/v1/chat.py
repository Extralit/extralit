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

"""
Chat endpoint using LiteLLM with GitHub Copilot.
"""

import logging
import os
from typing import Any

import litellm
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from extralit_server.models import User
from extralit_server.security import auth
from extralit_server.utils.auth_helpers import GitHubDeviceFlowAuth
from extralit_server.utils.litellm_context import LiteLLMContext

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    model: str = Field(default="copilot", description="Model to use for chat (e.g., 'copilot')")
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    stream: bool = Field(default=True, description="Whether to stream the response")


# VS Code headers to mimic for GitHub Copilot compatibility
COPILOT_HEADERS = {
    "Editor-Version": "vscode/1.96.2",
    "Editor-Plugin-Version": "copilot/1.256.0",
    "User-Agent": "GithubCopilot/1.256.0",
    "Copilot-Integration-Id": "vscode-chat",
}


def resolve_model_string(model: str) -> str:
    """
    Resolve user-friendly model names to LiteLLM model strings.

    Args:
        model: User-provided model name (e.g., "copilot", "gpt-4")

    Returns:
        LiteLLM-compatible model string
    """

    model_mapping = {
        "copilot": "gpt-4o",  # Updated to gpt-4o which is supported
        "github-copilot": "gpt-4o",
    }

    # If it's not in the map, use it as is, but strip github/ if present
    # to avoid duplication when we pass the provider explicitly
    resolved = model_mapping.get(model.lower(), model)
    return resolved.replace("github/", "")


@router.post("/chat")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(auth.get_current_user),
) -> StreamingResponse:
    """
    Chat endpoint using LiteLLM with GitHub Copilot.

    This endpoint requires the user to be authenticated with both Extralit
    and GitHub (via the /auth/github/login flow).

    Args:
        request: Chat request with model and messages
        current_user: Authenticated Extralit user

    Returns:
        StreamingResponse with chat completion

    Raises:
        HTTPException: If user is not authenticated with GitHub
    """
    # Check if user has GitHub token
    github_auth = GitHubDeviceFlowAuth(username=current_user.username)
    if not github_auth.is_authenticated():
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with GitHub. Please call /auth/github/login first.",
        )

    # Load the token to set in environment
    token_data = github_auth.load_token()
    if not token_data or "access_token" not in token_data:
        raise HTTPException(
            status_code=401,
            detail="Invalid GitHub token. Please re-authenticate.",
        )

    # Resolve model string
    litellm_model = resolve_model_string(request.model)

    _LOGGER.info(f"Chat request from {current_user.username} using model {litellm_model}")

    # Convert messages to LiteLLM format
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

    async def stream_response():
        """Stream the chat completion response."""
        try:
            # Use context manager for environment isolation
            with LiteLLMContext(username=current_user.username):
                # Set GitHub token in environment for LiteLLM
                os.environ["GITHUB_TOKEN"] = token_data["access_token"]
                os.environ["OPENAI_API_KEY"] = token_data["access_token"]  # Backup

                try:
                    # Call LiteLLM with streaming
                    response = await litellm.acompletion(
                        model=litellm_model,
                        messages=messages,
                        stream=request.stream,
                        extra_headers=COPILOT_HEADERS,
                        custom_llm_provider="github",
                    )

                    if request.stream:
                        # Stream the response chunks
                        async for chunk in response:
                            if chunk.choices and len(chunk.choices) > 0:
                                delta = chunk.choices[0].delta
                                if hasattr(delta, "content") and delta.content:
                                    # Send as SSE format (Standard Extralit/ChatGPT format)
                                    yield f"data: {delta.content}\n\n"
                        yield "data: [DONE]\n\n"
                    else:
                        # Non-streaming response
                        if response.choices and len(response.choices) > 0:
                            content = response.choices[0].message.content
                            yield f"data: {content}\n\n"
                            yield "data: [DONE]\n\n"
                finally:
                    # Clean up token from environment
                    os.environ.pop("GITHUB_TOKEN", None)
                    os.environ.pop("OPENAI_API_KEY", None)

        except Exception as e:
            _LOGGER.error(f"Error in chat completion for {current_user.username}: {e}")
            # Ensure the error is returned in a format the frontend can handle
            error_msg = str(e).replace('"', '\\"')
            yield f'data: {{"error": "{error_msg}"}}\n\n'

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
    )


@router.get("/chat/models")
async def list_models(current_user: User = Depends(auth.get_current_user)) -> dict[str, Any]:
    """
    List available chat models.

    Returns:
        Dictionary with available models
    """
    return {
        "models": [
            {
                "id": "copilot",
                "name": "GitHub Copilot",
                "description": "GitHub Copilot chat model",
                "requires_auth": True,
            },
        ],
    }
