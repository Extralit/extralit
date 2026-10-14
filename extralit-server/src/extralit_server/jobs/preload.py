"""
Preload heavy modules before RQ worker fork to improve job initialization performance.

This module should be imported before starting RQ workers to ensure all heavy
dependencies are loaded in the parent process before forking worker processes.
"""

from extralit_server.api.schemas.v1.document.metadata import DocumentProcessingMetadata  # noqa: F401
from extralit_server.contexts import files, imports, search  # noqa: F401
from extralit_server.contexts.document.margin import PDFAnalyzer  # noqa: F401
from extralit_server.contexts.document.preprocessing import PDFPreprocessingSettings, PDFPreprocessor  # noqa: F401
from extralit_server.contexts.ocr.triage import triage_pdf  # noqa: F401
from extralit_server.database import AsyncSessionLocal, async_engine  # noqa: F401
from extralit_server.jobs import (  # noqa: F401
    dataset_jobs,
    document_jobs,
    hub_jobs,
    import_jobs,
    ocr_jobs,
    webhook_jobs,
)
from extralit_server.models.database import Dataset, Document, Record, User, Workspace  # noqa: F401

# Search engine modules
try:
    from extralit_server.search_engine.elasticsearch import ElasticSearchEngine  # noqa: F401
except ImportError:
    pass


# Common ML/processing libraries that may be used in jobs
import asyncio  # noqa: F401
from datetime import datetime, timezone  # noqa: F401
from uuid import UUID  # noqa: F401

# RQ related imports
from rq import Retry, get_current_job  # noqa: F401
from rq.decorators import job  # noqa: F401

print("Preloaded heavy modules for RQ worker optimization")
