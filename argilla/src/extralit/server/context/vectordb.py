from typing import Optional
import os
from urllib.parse import urlparse

import weaviate
from weaviate import WeaviateClient
from weaviate.auth import AuthApiKey
from weaviate.exceptions import WeaviateStartUpError
from weaviate.classes.init import AdditionalConfig, Timeout


def get_weaviate_client(default_http_port=8080, default_grpc_port=50051) -> Optional[WeaviateClient]:
    if 'WCS_HTTP_URL' not in os.environ:
        return None

    try:
        api_keys = os.getenv('WCS_API_KEY', '').split(',')
        api_key_credentials = AuthApiKey(api_keys[0]) if api_keys and api_keys[0] else None

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
                auth_credentials=api_key_credentials,
                additional_config=AdditionalConfig(
                    timeout=Timeout(init=30, query=60, insert=120)  # Values in seconds
                )
            )
        else:
            weaviate_client = weaviate.connect_to_custom(
                http_host=http_host,
                http_port=http_url.port or default_http_port,
                http_secure=http_url.scheme == 'https',
                grpc_host=grpc_host,
                grpc_port=grpc_url.port or default_grpc_port,
                grpc_secure=grpc_url.scheme == 'https',
                auth_credentials=api_key_credentials,
                additional_config=AdditionalConfig(
                    timeout=Timeout(init=30, query=60, insert=120)  # Values in seconds
                )
            )

        return weaviate_client
    
    except WeaviateStartUpError as wsue:
        print(f"Failed to start Weaviate: {wsue}")
    
    except Exception as e:
        raise Exception(f"Unable to connect to Weaviate instance with WCS_HTTP_URL {http_url} and WCS_GRPC_URL {grpc_url}.") from e

    return None