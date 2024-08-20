import logging
import os
from typing import Optional, Union

from langfuse.llama_index import LlamaIndexCallbackHandler
from langfuse.utils.base_callback_handler import LangfuseBaseCallbackHandler
from llama_index.core import Settings, set_global_handler

_LOGGER = logging.getLogger(__name__)

def get_langfuse_callback(
        langfuse_public_key: Optional[str] = None,
        langfuse_secret_key: Optional[str] = None) -> Union[LangfuseBaseCallbackHandler, LlamaIndexCallbackHandler]:
    try:
        langfuse_callback_handler = LlamaIndexCallbackHandler(
            host=os.getenv('LANGFUSE_HOST'),
            public_key=langfuse_public_key if langfuse_public_key else os.getenv('LANGFUSE_PUBLIC_KEY'),
            secret_key=langfuse_secret_key if langfuse_secret_key else os.getenv('LANGFUSE_SECRET_KEY'),
        )
        if not Settings.callback_manager.handlers:
            Settings.callback_manager.add_handler(langfuse_callback_handler)
        set_global_handler("langfuse")
    except Exception as e:
        _LOGGER.error(f"Failed to create Langfuse callback handler: {e}")
        langfuse_callback_handler = None

    return langfuse_callback_handler
