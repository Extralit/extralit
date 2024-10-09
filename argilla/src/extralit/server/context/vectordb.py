from typing import Optional
import os
from urllib.parse import urlparse

import weaviate
from weaviate import WeaviateClient
from weaviate.exceptions import WeaviateStartUpError


def get_weaviate_client(http_port=None, http_secure=None, grpc_port=None, grpc_secure=None) -> Optional[WeaviateClient]:
    if 'WCS_HTTP_URL' not in os.environ:
        print("WCS_HTTP_URL not set")
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
            http_host=http_url.hostname,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=grpc_url.hostname,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
            auth_credentials=weaviate.auth.AuthApiKey(api_keys[0]),
            headers={
                "X-OpenAI-Api-Key": os.environ["OPENAI_API_KEY"]
            } if "OPENAI_API_KEY" in os.environ else None
        )

        return weaviate_client
    
    except WeaviateStartUpError as wsue:
        print(f"Failed to start Weaviate: {wsue}")
    
    except Exception as e:
        raise e


    return None