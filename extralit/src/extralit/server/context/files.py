import os
from typing import Optional
from urllib.parse import urlparse
from minio import Minio
import logging

_LOGGER = logging.getLogger("extralit")


def get_minio_client() -> Optional[Minio]:
    s3_endpoint = os.getenv('S3_ENDPOINT')
    s3_access_key = os.getenv('S3_ACCESS_KEY')
    s3_secret_key = os.getenv('S3_SECRET_KEY')

    if s3_endpoint is None:
        return None

    try:
        parsed_url = urlparse(s3_endpoint)
        hostname = parsed_url.hostname
        port = parsed_url.port

        if hostname is None:
            _LOGGER.error(f"Invalid URL: no hostname in S3_ENDPOINT found, possible due to lacking http(s) protocol. Given '{s3_endpoint}'")
            return None

        return Minio(
            endpoint=f'{hostname}:{port}' if port else hostname,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            secure=parsed_url.scheme == "https",
        )
    except Exception as e:
        _LOGGER.error(f"Error creating Minio client: {e}", stack_info=True)
        return None
