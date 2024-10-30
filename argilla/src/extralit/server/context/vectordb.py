from typing import Optional
import os
from urllib.parse import urlparse

import weaviate
from weaviate import WeaviateClient
from weaviate.auth import AuthApiKey
from weaviate.exceptions import WeaviateStartUpError


def get_weaviate_client(http_port=8080, http_secure=True, grpc_port=50051, grpc_secure=True) -> Optional[WeaviateClient]:
    if 'WCS_HTTP_URL' not in os.environ:
        return None

    try:
        api_keys = os.getenv('WCS_API_KEY', '').split(',')

        # Parse HTTP URL
        http_url = urlparse(os.getenv("WCS_HTTP_URL"))
        http_host = http_url.hostname or http_url.path

        # Parse GRPC URL
        grpc_url = urlparse(os.getenv('WCS_GRPC_URL'))
        grpc_host = grpc_url.hostname or grpc_url.path

        if http_host.endswith('weaviate.cloud'):
            # Connect to Weaviate Cloud
            weaviate_client = weaviate.connect_to_weaviate_cloud(
                cluster_url=http_url.geturl(),
                auth_credentials=AuthApiKey(api_keys[0]) if api_keys and api_keys[0] else None,
            )
        else:
            weaviate_client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_url.port or http_port,
                http_secure=http_url.scheme == 'https' or http_secure,
                grpc_host=grpc_host,
                grpc_port=grpc_url.port or grpc_port,
                grpc_secure=grpc_url.scheme == 'https' or grpc_secure,
                auth_credentials=AuthApiKey(api_keys[0]) if api_keys and api_keys[0] else None,
            )

        return weaviate_client
    
    except WeaviateStartUpError as wsue:
        print(f"Failed to start Weaviate: {wsue}")
    
    except Exception as e:
        raise Exception(f"Unable to connect to Weaviate instance with WCS_HTTP_URL {http_url} and WCS_GRPC_URL {grpc_url}.") from e

    return None