import os

import argilla as rg

def get_argilla_client():
    return rg.Argilla(
        api_url=os.getenv('ARGILLA_BASE_URL'),
        api_key=os.getenv('ARGILLA_API_KEY'),
    )
