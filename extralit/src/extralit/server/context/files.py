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

import os
from typing import Optional
from urllib.parse import urlparse
from minio import Minio
import logging

_LOGGER = logging.getLogger(__name__)


def get_minio_client() -> Optional[Minio]:
    s3_endpoint = os.getenv("S3_ENDPOINT")
    s3_access_key = os.getenv("S3_ACCESS_KEY")
    s3_secret_key = os.getenv("S3_SECRET_KEY")

    if s3_endpoint is None:
        return None

    try:
        parsed_url = urlparse(s3_endpoint)
        hostname = parsed_url.hostname
        port = parsed_url.port

        if hostname is None:
            _LOGGER.error(
                f"Invalid URL: no hostname in S3_ENDPOINT found, possible due to lacking http(s) protocol. Given '{s3_endpoint}'"
            )
            return None

        return Minio(
            endpoint=f"{hostname}:{port}" if port else hostname,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            secure=parsed_url.scheme == "https",
        )
    except Exception as e:
        _LOGGER.error(f"Error creating Minio client: {e}", stack_info=True)
        return None
