import re
from typing import Dict, List, Iterator, Any

from langfuse import Langfuse
from langfuse.api import ObservationsView

from extralit.extraction.models import PaperExtraction
from extralit.metrics.extraction import grits_multi_tables
from extralit.server.context.llamaindex import get_langfuse_callback

langfuse_callback = get_langfuse_callback()
langfuse_client = langfuse_callback.langfuse


def get_langfuse_traces(
        langfuse_client: Langfuse,
        user_id: str,
        references: List[str]=None,
        schema_names: List[str]=None,
        input_match='Please complete the following',
        page_size=50) -> Iterator[ObservationsView]:

    page = 1
    max_page = None
    while max_page is None or page <= max_page:
        traces_batch = langfuse_client.get_observations(user_id=user_id, limit=page_size, page=page)
        max_page = traces_batch.meta.total_pages

        for trace in traces_batch.data:
            if trace is None or not trace.metadata: continue
            trace_metadata: dict = trace.metadata.get('metadata', {}) or {}
            if references and not next((metadata.get('reference') in references \
                                        for metadata in trace_metadata.values()), None):
                continue
            if input_match and not re.search(input_match, trace.input): continue
            # if schema_names and not next((metadata.get('schema') in schema_names for metadata in trace.metadata.values()), None):
            #     continue
            if not isinstance(trace.output, dict) or not trace.output.get('items', []): continue

            yield trace

        page += 1

