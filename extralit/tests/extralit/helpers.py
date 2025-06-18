import contextlib
import os
from pathlib import Path
import sys
from typing import Any, Generator, List, Optional
import openai

from openai.types.completion import Completion, CompletionChoice, CompletionUsage
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice

def mock_completion_stream_v1(
    *args: Any, **kwargs: Any
) -> Generator[Completion, None, None]:
    responses = [
        Completion(
            id="cmpl-uqkvlQyYK7bGYrRHQ0eXlWi7",
            object="text_completion",
            created=1589478378,
            model="text-davinci-003",
            choices=[CompletionChoice(text="1", finish_reason="stop", index=0)],
        ),
        Completion(
            id="cmpl-uqkvlQyYK7bGYrRHQ0eXlWi7",
            object="text_completion",
            created=1589478378,
            model="text-davinci-003",
            choices=[CompletionChoice(text="2", finish_reason="stop", index=0)],
        ),
    ]
    yield from responses


def mock_chat_completion_stream_v1(
    responses: List[str], chat_id="chatcmpl-6ptKyqKOGXZT6iQnqiXAH8adNLUzD", object="chat.completion.chunk", created=1677825464,
    model="gpt-3.5-turbo-0301",
    *args: Any, **kwargs: Any
) -> Generator[ChatCompletionChunk, None, None]:
    
    responses = [
        ChatCompletionChunk(
            id=chat_id,
            object=object,
            created=created,
            model=model,
            choices=[
                ChunkChoice(
                    delta=ChoiceDelta(role="assistant"), finish_reason=None, index=0
                )
            ],
        ),
        *[
            ChatCompletionChunk(
                id=chat_id,
                object=object,
                created=created,
                model=model,
                choices=[
                    ChunkChoice(delta=ChoiceDelta(content=content), finish_reason=None, index=0)
                ],
            ) for content in responses
        ],
        ChatCompletionChunk(
            id=chat_id,
            object=object,
            created=created,
            model=model,
            choices=[ChunkChoice(delta=ChoiceDelta(), finish_reason="stop", index=0)],
        ),
    ]
    yield from responses

