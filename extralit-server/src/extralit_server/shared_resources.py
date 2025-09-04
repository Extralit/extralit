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
Shared resources module to store application-wide resources like S3 client.
This module is separate from _app.py to avoid circular imports.
"""

import aioboto3

from extralit_server.settings import settings

# Global storage for shared resources (following FastAPI pattern)
shared_resources = {}


async def initialize_s3_client():
    """Initialize S3 client with settings configuration."""
    if not all([settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key]):
        raise ValueError("S3 configuration required: s3_endpoint, s3_access_key, s3_secret_key")

    session = aioboto3.Session(
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region or "us-east-1",
    )

    s3_client = await session.client(  # pyright: ignore[reportGeneralTypeIssues]
        "s3",
        endpoint_url=settings.s3_endpoint,
        use_ssl=settings.s3_endpoint.startswith("https://") if settings.s3_endpoint else True,
    ).__aenter__()

    shared_resources["s3_client"] = s3_client
    return s3_client
