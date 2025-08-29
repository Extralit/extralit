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

from unittest.mock import patch

import pytest
from httpx import Timeout

from extralit import Extralit


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
