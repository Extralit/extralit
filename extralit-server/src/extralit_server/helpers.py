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
Common helper functions
"""

import logging
from typing import TYPE_CHECKING

import aioboto3

from extralit_server.settings import settings

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client

_LOGGER = logging.getLogger("extralit_server")
shared_resources = {}


async def create_s3_client() -> "S3Client":
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


def remove_suffix(text: str, suffix: str):
    # TODO Move where is used
    """Give a text, removes suffix substring from it"""
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def replace_string_in_file(filename: str, string: str, replace_by: str, encoding: str = "utf-8"):
    # TODO Move where is used
    """Read a file and replace an old value in file by a new one"""
    # Safely read the input filename using 'with'
    with open(filename, encoding=encoding) as f:
        data = f.read()
        if string not in data:
            return

    # Safely write the changed content, if found in the file
    with open(filename, mode="w", encoding=encoding) as f:
        data = data.replace(string, replace_by)
        f.write(data)
