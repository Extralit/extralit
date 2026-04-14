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
Chat endpoint using LiteLLM with GitHub Copilot and RAG support.
"""

import json
import logging
from typing import Annotated, Any
from uuid import UUID

import litellm
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from extralit_server.contexts import datasets as dataset_ctx
from extralit_server.database import get_async_db
from extralit_server.models import Dataset, User, VectorSettings
from extralit_server.search_engine import SearchEngine, get_search_engine
from extralit_server.security import auth
from extralit_server.utils.auth_helpers import load_token

_LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

COPILOT_HEADERS = {
    "Editor-Version": "vscode/1.96.2",
    "Editor-Plugin-Version": "copilot/1.256.0",
    "User-Agent": "GithubCopilot/1.256.0",
    "Copilot-Integration-Id": "vscode-chat",
}


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., description="Role of the message sender (user, assistant, system)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    model: str = Field(default="copilot", description="Model to use for chat (e.g., 'copilot')")
    messages: list[ChatMessage] = Field(..., description="List of chat messages")
    stream: bool = Field(default=True, description="Whether to stream the response")
    dataset_id: UUID | None = Field(default=None, description="Optional dataset ID for RAG retrieval")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve for RAG")


def resolve_model_string(model: str) -> str:
    """Resolve user-friendly model names to LiteLLM ``github_copilot/`` model strings."""
    model_mapping = {
        "copilot": "github_copilot/gpt-4o",
        "github-copilot": "github_copilot/gpt-4o",
    }
    resolved = model_mapping.get(model.lower(), model)
    # Ensure the github_copilot/ prefix is present
    if not resolved.startswith("github_copilot/"):
        resolved = f"github_copilot/{resolved}"
    return resolved


async def retrieve_context(
    db: AsyncSession,
    search_engine: SearchEngine,
    dataset_id: UUID,
    query_text: str,
    github_token: str,
    top_k: int = 5,
) -> str | None:
    """
    Retrieve relevant context from a dataset using RAG.

    Args:
        db: Database session
        search_engine: Search engine instance
        dataset_id: ID of the dataset to search
        query_text: User's query text
        github_token: GitHub token for embedding API
        top_k: Number of results to retrieve

    Returns:
        Formatted context string or None if retrieval fails
    """
    try:
        # Fetch the dataset
        dataset = await Dataset.get_by(db, id=dataset_id)
        if not dataset:
            _LOGGER.warning(f"Dataset {dataset_id} not found")
            return None

        # Get vector settings for this dataset (use first available or "default")
        vector_settings = await VectorSettings.get_by(db, dataset_id=dataset.id)
        if not vector_settings:
            _LOGGER.warning(f"No vector settings found for dataset {dataset_id}")
            return None

        _LOGGER.info(f"Generating embedding for query: {query_text[:50]}...")

        embedding_response = await litellm.aembedding(
            model="github_copilot/text-embedding-3-small",
            input=query_text,
            custom_llm_provider="github",
            api_key=github_token,
        )
        query_embedding = embedding_response["data"][0]["embedding"]

        _LOGGER.info(f"Generated embedding with {len(query_embedding)} dimensions")

        # Perform similarity search
        search_results = await search_engine.similarity_search(
            dataset=dataset,
            vector_settings=vector_settings,
            value=query_embedding,
            max_results=top_k,
            threshold=0.6,  # Minimum similarity threshold
        )

        if not search_results.items:
            _LOGGER.info("No relevant documents found")
            return None

        _LOGGER.info(f"Found {len(search_results.items)} relevant documents")

        # Fetch the actual record data
        record_ids = [item.record_id for item in search_results.items]
        records = await dataset_ctx.get_records_by_ids(
            db=db,
            dataset_id=dataset.id,
            records_ids=record_ids,
        )

        # Build context from retrieved records
        context_chunks = []
        for record in records:
            # Extract text from record fields
            if record.fields:
                for field_name, field_value in record.fields.items():
                    if isinstance(field_value, str):
                        context_chunks.append(f"[{field_name}]: {field_value}")
                    elif isinstance(field_value, list):
                        # Handle chat fields (list of messages)
                        for msg in field_value:
                            if isinstance(msg, dict) and "content" in msg:
                                context_chunks.append(f"[{field_name}]: {msg['content']}")

        if not context_chunks:
            _LOGGER.warning("No text content found in retrieved records")
            return None

        context = "\n\n".join(context_chunks[: top_k * 3])  # Limit total context
        _LOGGER.info(f"Built context with {len(context)} characters from {len(context_chunks)} chunks")

        return context

    except Exception as e:
        _LOGGER.error(f"Error during RAG retrieval: {e}", exc_info=True)
        return None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    search_engine: Annotated[SearchEngine, Depends(get_search_engine)],
    current_user: User = Depends(auth.get_current_user),
) -> StreamingResponse:
    """
    Chat endpoint using LiteLLM with GitHub Copilot and optional RAG.

    This endpoint requires the user to be authenticated with both Extralit
    and GitHub (via the /auth/github/login flow).

    If dataset_id is provided, the endpoint will perform RAG retrieval:
    1. Generate embedding for the user's query
    2. Search for relevant documents in the dataset
    3. Inject retrieved context into the system prompt

    Args:
        request: Chat request with model, messages, and optional dataset_id
        current_user: Authenticated Extralit user
        db: Database session (injected for RAG)
        search_engine: Search engine instance (injected for RAG)

    Returns:
        StreamingResponse with chat completion

    Raises:
        HTTPException: If user is not authenticated with GitHub
    """
    # Check if user has a valid GitHub token
    token_data = load_token(current_user.username)
    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated with GitHub. Please call /auth/github/login first.",
        )

    # Resolve model string
    litellm_model = resolve_model_string(request.model)

    _LOGGER.info(
        f"Chat request from {current_user.username} using model {litellm_model}"
        + (f" with RAG (dataset_id={request.dataset_id})" if request.dataset_id else "")
    )

    # Convert messages to LiteLLM format
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

    # RAG: Retrieve context if dataset_id is provided
    context = None
    if request.dataset_id:
        # Extract user's last message as query
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if user_messages:
            query_text = user_messages[-1]["content"]
            context = await retrieve_context(
                db=db,
                search_engine=search_engine,
                dataset_id=request.dataset_id,
                query_text=query_text,
                github_token=token_data["access_token"],
                top_k=request.top_k,
            )

    # Inject context into messages if available
    if context:
        system_message = {
            "role": "system",
            "content": (
                "You are a helpful assistant. Use the following context from the knowledge base "
                "to answer the user's question. If the context doesn't contain relevant information, "
                "you can use your general knowledge but mention that the information isn't in the context.\n\n"
                f"Context:\n{context}"
            ),
        }
        # Insert system message at the beginning
        messages = [system_message, *messages]
        _LOGGER.info(f"Injected RAG context ({len(context)} chars) into conversation")

    async def stream_response():
        """Stream the chat completion response."""
        try:
            response = await litellm.acompletion(
                model=litellm_model,
                messages=messages,
                stream=request.stream,
                api_key=token_data["access_token"],
                extra_headers=COPILOT_HEADERS,
                custom_llm_provider="github",
            )

            if request.stream:
                async for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content") and delta.content:
                            yield f"data: {delta.content}\n\n"
                yield "data: [DONE]\n\n"
            else:
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    yield f"data: {content}\n\n"
                yield "data: [DONE]\n\n"

        except Exception as e:
            _LOGGER.error("Chat completion error for %s: %s", current_user.username, e)
            yield f"data: {json.dumps({'error': 'Chat completion failed. Please try again.'})}\n\n"

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
                "description": "GitHub Copilot chat model with optional RAG support",
                "requires_auth": True,
                "supports_rag": True,
            },
        ],
    }
