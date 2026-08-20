"""Assert the endpoints `extralit._api` calls exist in the committed server contract.

Reads `openapi/v1.json` as data — the SDK never imports server code, so this catches a server
renaming or dropping an endpoint without needing a running instance.
"""

import json
import re
from pathlib import Path

import pytest

COMMITTED_SPEC = Path(__file__).parents[3] / "openapi" / "v1.json"

# The artifact is the v1 sub-app's own document, so its paths omit the mount prefix.
API_PREFIX = "/api/v1"

HTTP_METHODS = ("get", "post", "put", "patch", "delete")

# (method, url) pairs as they appear in extralit/src/extralit/_api/*.py.
SDK_ENDPOINTS = [
    # _datasets.py
    ("POST", "/api/v1/datasets"),
    ("GET", "/api/v1/datasets/{dataset_id}"),
    ("PATCH", "/api/v1/datasets/{dataset_id}"),
    ("DELETE", "/api/v1/datasets/{dataset_id}"),
    ("GET", "/api/v1/datasets/{dataset_id}/progress"),
    ("GET", "/api/v1/datasets/{dataset_id}/users/progress"),
    ("PUT", "/api/v1/datasets/{dataset_id}/publish"),
    ("GET", "/api/v1/me/datasets"),
    # _workspaces.py
    ("POST", "/api/v1/workspaces"),
    ("GET", "/api/v1/workspaces/{workspace_id}"),
    ("DELETE", "/api/v1/workspaces/{workspace_id}"),
    ("GET", "/api/v1/me/workspaces"),
    ("GET", "/api/v1/users/{user_id}/workspaces"),
    ("POST", "/api/v1/workspaces/{workspace_id}/doctor"),
    ("GET", "/api/v1/files/{workspace_name}/{path}"),
    ("GET", "/api/v1/file/{workspace_name}/{path}"),
    ("POST", "/api/v1/file/{workspace_name}/{path}"),
    ("DELETE", "/api/v1/file/{workspace_name}/{path}"),
    # _records.py
    ("GET", "/api/v1/records/{record_id}"),
    ("PATCH", "/api/v1/records/{record_id}"),
    ("DELETE", "/api/v1/records/{record_id}"),
    ("POST", "/api/v1/records/{record_id}/responses"),
    ("GET", "/api/v1/datasets/{dataset_id}/records"),
    ("DELETE", "/api/v1/datasets/{dataset_id}/records"),
    ("POST", "/api/v1/datasets/{dataset_id}/records/search"),
    ("POST", "/api/v1/datasets/{dataset_id}/records/bulk"),
    ("PUT", "/api/v1/datasets/{dataset_id}/records/bulk"),
    # _users.py
    ("GET", "/api/v1/users"),
    ("POST", "/api/v1/users"),
    ("GET", "/api/v1/users/{user_id}"),
    ("PATCH", "/api/v1/users/{user_id}"),
    ("DELETE", "/api/v1/users/{user_id}"),
    ("GET", "/api/v1/me"),
    ("GET", "/api/v1/workspaces/{workspace_id}/users"),
    ("POST", "/api/v1/workspaces/{workspace_id}/users"),
    ("DELETE", "/api/v1/workspaces/{workspace_id}/users/{user_id}"),
    # _fields.py
    ("GET", "/api/v1/datasets/{dataset_id}/fields"),
    ("POST", "/api/v1/datasets/{dataset_id}/fields"),
    ("PATCH", "/api/v1/fields/{field_id}"),
    ("DELETE", "/api/v1/fields/{field_id}"),
    # _questions.py
    ("GET", "/api/v1/datasets/{dataset_id}/questions"),
    ("POST", "/api/v1/datasets/{dataset_id}/questions"),
    ("PATCH", "/api/v1/questions/{question_id}"),
    ("DELETE", "/api/v1/questions/{question_id}"),
    # _metadata.py
    ("POST", "/api/v1/datasets/{dataset_id}/metadata-properties"),
    ("PATCH", "/api/v1/metadata-properties/{metadata_id}"),
    ("DELETE", "/api/v1/metadata-properties/{metadata_id}"),
    ("GET", "/api/v1/me/datasets/{dataset_id}/metadata-properties"),
    # _vectors.py
    ("GET", "/api/v1/datasets/{dataset_id}/vectors-settings"),
    ("POST", "/api/v1/datasets/{dataset_id}/vectors-settings"),
    ("PATCH", "/api/v1/vectors-settings/{vector_id}"),
    ("DELETE", "/api/v1/vectors-settings/{vector_id}"),
    # _webhooks.py
    ("GET", "/api/v1/webhooks"),
    ("POST", "/api/v1/webhooks"),
    ("PATCH", "/api/v1/webhooks/{webhook_id}"),
    ("DELETE", "/api/v1/webhooks/{webhook_id}"),
    ("POST", "/api/v1/webhooks/{webhook_id}/ping"),
    # _documents.py
    ("GET", "/api/v1/documents"),
    ("POST", "/api/v1/documents"),
    ("PATCH", "/api/v1/documents/{document_id}"),
    ("GET", "/api/v1/documents/workspace/{workspace_id}"),
    ("DELETE", "/api/v1/documents/workspace/{workspace_id}"),
]


def _erase_param_names(path: str) -> str:
    """SDK and server name the same path parameter differently; only the route shape matters."""
    return re.sub(r"\{[^}]*\}", "{}", path)


@pytest.fixture(scope="module")
def contract() -> set:
    spec = json.loads(COMMITTED_SPEC.read_text())
    return {
        (method.upper(), _erase_param_names(path))
        for path, operations in spec["paths"].items()
        for method in operations
        if method in HTTP_METHODS
    }


@pytest.mark.parametrize(("method", "url"), SDK_ENDPOINTS)
def test_sdk_endpoint_exists_in_contract(contract, method, url):
    path = _erase_param_names(url.removeprefix(API_PREFIX))

    assert (method, path) in contract, (
        f"The SDK calls {method} {url}, which is not in {COMMITTED_SPEC.name}. "
        f"Either the server dropped it or the SDK needs updating."
    )


def test_manifest_has_no_duplicates():
    assert len(SDK_ENDPOINTS) == len(set(SDK_ENDPOINTS))
