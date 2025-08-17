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
RQ client for PyMuPDF PDF extraction service.
"""

import logging
import os
from typing import Any, Optional

import redis
from rq import Queue
from rq.job import Job

_LOGGER = logging.getLogger(__name__)

# Configuration from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EXTRACTION_QUEUE_NAME = os.getenv("PYMUPDF_EXTRACTION_QUEUE", "extraction")

# Global Redis connection and queue (following rq_pymupdf pattern)
_redis = None
_extraction_queue = None


def get_redis_connection():
    """Get or create Redis connection."""
    global _redis
    if _redis is None:
        _redis = redis.from_url(REDIS_URL)
    return _redis


def get_extraction_queue():
    """Get or create extraction queue."""
    global _extraction_queue
    if _extraction_queue is None:
        _extraction_queue = Queue(EXTRACTION_QUEUE_NAME, connection=get_redis_connection())
    return _extraction_queue


def enqueue_pdf_extraction(
    pdf_bytes: bytes,
    filename: str,
    analysis_metadata: Optional[dict[str, Any]] = None,
    extraction_config: Optional[dict[str, Any]] = None,
    job_timeout: int = 600,
) -> str:
    """Enqueue a PDF extraction job for background processing."""
    try:
        queue = get_extraction_queue()

        job = queue.enqueue(
            "src.jobs.extraction_jobs.extract_pdf_markdown_job",
            pdf_bytes=pdf_bytes,
            filename=filename,
            analysis_metadata=analysis_metadata,
            extraction_config=extraction_config,
            job_timeout=job_timeout,
            result_ttl=3600,
            failure_ttl=86400,
            description=f"extract_pdf:{filename}",
        )

        job_id = job.get_id()
        _LOGGER.info(f"Enqueued PDF extraction job {job_id} for {filename}")
        return job_id

    except redis.ConnectionError as e:
        _LOGGER.error(f"Redis connection failed when enqueueing job for {filename}: {e}")
        raise
    except Exception as e:
        _LOGGER.error(f"Failed to enqueue PDF extraction job for {filename}: {e}")
        raise


def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status and result of a PDF extraction job."""
    try:
        queue = get_extraction_queue()
        job = Job.fetch(job_id, connection=queue.connection)

        result = {
            "job_id": job_id,
            "status": job.get_status(),
            "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }

        if job.is_failed:
            result["error"] = str(job.exc_info or "Job failed without error details")
            _LOGGER.warning(f"Job {job_id} failed: {result['error']}")

        if job.is_finished and job.result:
            result["result"] = job.result
            if job.result.get("ok", False):
                _LOGGER.info(f"Job {job_id} completed successfully")
            else:
                _LOGGER.warning(f"Job {job_id} completed with errors: {job.result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        _LOGGER.error(f"Failed to get status for job {job_id}: {e}")
        raise


def cancel_job(job_id: str) -> bool:
    """Cancel a queued or running job."""
    try:
        queue = get_extraction_queue()
        job = Job.fetch(job_id, connection=queue.connection)

        if job.get_status() in ["queued", "started"]:
            job.cancel()
            _LOGGER.info(f"Cancelled job {job_id}")
            return True
        else:
            _LOGGER.warning(f"Cannot cancel job {job_id} with status {job.get_status()}")
            return False

    except Exception as e:
        _LOGGER.error(f"Failed to cancel job {job_id}: {e}")
        return False


def is_redis_available() -> bool:
    """Check if Redis is available for RQ operations."""
    try:
        conn = get_redis_connection()
        conn.ping()
        return True
    except Exception as e:
        _LOGGER.warning(f"Redis health check failed: {e}")
        return False
