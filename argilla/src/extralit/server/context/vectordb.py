from typing import Optional
import os

import weaviate
from weaviate import WeaviateClient
from weaviate.exceptions import WeaviateStartUpError


def get_weaviate_client(http_port=80, http_secure=False, grpc_port=50051, grpc_secure=False) -> Optional[WeaviateClient]:
    if 'WCS_HTTP_URL' not in os.environ:
        print("WCS_HTTP_URL not set")
        return None

    try:
        api_keys = os.getenv('WCS_API_KEY', '').split(',')

        weaviate_client = weaviate.connect_to_custom(
            http_host=os.getenv("WCS_HTTP_URL"),
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=os.getenv('WCS_GRPC_URL'),
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
            auth_credentials=weaviate.auth.AuthApiKey(api_keys[0]),
            headers={
                "X-OpenAI-Api-Key": os.environ["OPENAI_API_KEY"]
            }
        )

        return weaviate_client
    
    except WeaviateStartUpError as wsue:
        print(f"Failed to start Weaviate: {wsue}")
    
    except Exception as e:
        raise e


    return None