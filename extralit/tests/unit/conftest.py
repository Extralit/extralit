from unittest.mock import patch

import pytest
from httpx import Timeout

from extralit import Extralit


def pytest_collection_modifyitems(items):
    # pytest-httpx>=0.30 defaults are stricter than the 0.29 behaviour these tests rely on
    for item in items:
        item.add_marker(
            pytest.mark.httpx_mock(can_send_already_matched_responses=True, assert_all_requests_were_expected=False)
        )


@pytest.fixture(autouse=True)
def mock_validate_connection():
    with patch("extralit._api._client.APIClient._validate_connection") as mocked_validator:
        yield mocked_validator


# Example usage in a test module
def test_create_default_client(mock_validate_connection):
    http_client = Extralit().http_client

    assert http_client is not None
    assert http_client.base_url == "http://localhost:6900"
    assert http_client.timeout == Timeout(60)
    assert http_client.headers["X-Extralit-Api-Key"] == "extralit.apikey"
