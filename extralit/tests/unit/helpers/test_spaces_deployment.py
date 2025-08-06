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

from unittest.mock import Mock, patch

import pytest
from huggingface_hub import SpaceStage

from extralit.client import Extralit


class TestSpacesDeploymentMixin:
    @pytest.fixture
    def extralit_client_class(self):
        return Extralit

    @patch("extralit._helpers._deploy.HfApi")
    @patch("extralit._helpers._deploy.get_token")
    @patch("extralit.client.Extralit.__init__", return_value=None)
    def test_deploy_on_spaces(self, mock_argilla_init, mock_get_token, mock_hf_api, extralit_client_class):
        mock_get_token.return_value = "fake_token"
        mock_api = Mock()
        mock_hf_api.return_value = mock_api
        mock_api.whoami.return_value = {"name": "test_user"}
        mock_api.repo_exists.return_value = False
        mock_api.get_space_runtime.return_value = Mock(stage=SpaceStage.RUNNING)

        result = extralit_client_class.deploy_on_spaces(api_key="12345678")

        assert isinstance(result, Extralit)
        mock_api.duplicate_space.assert_called_once()
        mock_api.create_repo.assert_called_once()
        mock_argilla_init.assert_called_once()

        # Check the arguments passed to Extralit.__init__
        args, kwargs = mock_argilla_init.call_args
        assert kwargs["api_key"] == "12345678"
        assert kwargs["api_url"].startswith("https://")
        assert kwargs["api_url"].endswith(".hf.space/")
        assert "headers" in kwargs

    @patch("extralit._helpers._deploy.get_token")
    @patch("extralit._helpers._deploy.login")
    def test_acquire_hf_token(self, mock_login, mock_get_token, extralit_client_class):
        mock_get_token.side_effect = [None, "fake_token"]
        token = extralit_client_class._acquire_hf_token(None)
        assert token == "fake_token"
        mock_login.assert_called_once()

    @pytest.mark.parametrize(
        "stage,expected",
        [
            (SpaceStage.RUNNING, False),
            (SpaceStage.BUILDING, False),
            (SpaceStage.PAUSED, True),
            (SpaceStage.STOPPED, True),
            ("INVALID", pytest.raises(ValueError)),
        ],
    )
    def test_is_space_stopped(self, stage, expected, extralit_client_class):
        if isinstance(expected, bool):
            assert extralit_client_class._is_space_stopped(stage) == expected
        else:
            with expected:
                extralit_client_class._is_space_stopped(stage)

    @pytest.mark.parametrize(
        "stage,expected",
        [
            (SpaceStage.RUNNING, False),
            (SpaceStage.RUNNING_BUILDING, True),
            (SpaceStage.BUILDING, True),
            (SpaceStage.PAUSED, False),
            (SpaceStage.STOPPED, False),
            ("INVALID", pytest.raises(ValueError)),
        ],
    )
    def test_is_building(self, stage, expected, extralit_client_class):
        if isinstance(expected, bool):
            assert extralit_client_class._is_building(stage) == expected
        else:
            with expected:
                extralit_client_class._is_building(stage)

    @pytest.mark.parametrize(
        "component,expected",
        [
            ("Test-Repo", "test-repo"),
            ("Test_Repo_123", "test-repo-123"),
            ("Test Repo!@#", "test-repo"),
            ("-test-repo-", "test-repo"),
        ],
    )
    def test_sanitize_url_component(self, component, expected, extralit_client_class):
        assert extralit_client_class._sanitize_url_component(component) == expected
