from typing import Optional
import os
from urllib.parse import urlparse

import weaviate
from weaviate import WeaviateClient
from weaviate.exceptions import WeaviateStartUpError


def get_weaviate_client(http_port=8080, http_secure=None, grpc_port=50051, grpc_secure=None) -> Optional[WeaviateClient]:
    if 'WCS_HTTP_URL' not in os.environ:
        return None

    try:
        api_keys = os.getenv('WCS_API_KEY', '').split(',')

        # Parse HTTP URL
        http_url = urlparse(os.getenv("WCS_HTTP_URL"))
        http_port = http_port or http_url.port
        http_secure = http_secure or http_url.scheme == 'https'

        # Parse GRPC URL
        grpc_url = urlparse(os.getenv('WCS_GRPC_URL'))
        grpc_port = grpc_port or grpc_url.port
        grpc_secure = grpc_secure or grpc_url.scheme == 'https'

        weaviate_client = weaviate.connect_to_custom(
            http_host=http_url.hostname or http_url.path,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=grpc_url.hostname or grpc_url.path,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
            auth_credentials=weaviate.auth.AuthApiKey(api_keys[0]) \
                if api_keys and api_keys[0] else None,
        )

        return weaviate_client
    
    except WeaviateStartUpError as wsue:
        print(f"Failed to start Weaviate: {wsue}")
    
    except Exception as e:
        raise e


    return None