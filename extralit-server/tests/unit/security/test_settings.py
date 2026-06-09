import os
import tempfile
from unittest import mock

from extralit_server.security.settings import Settings


def test_default_security_settings():
    settings = Settings()

    assert settings.algorithm == "HS256"
    assert settings.token_expiration == 86400
    assert settings.oauth_cfg == ".oauth.yaml"

    assert len(settings.secret_key) == 32


def test_configure_algorithm():
    algorithm = "mock-algorithm"
    with mock.patch.dict(os.environ, {"EXTRALIT_AUTH_ALGORITHM": algorithm}):
        settings = Settings()

        assert settings.algorithm == algorithm


def test_configure_token_expiration():
    token_expiration = 3600
    with mock.patch.dict(os.environ, {"EXTRALIT_AUTH_TOKEN_EXPIRATION": str(token_expiration)}):
        settings = Settings()

        assert settings.token_expiration == token_expiration


def test_configure_secret_key():
    secret_key = "mock-secret-key"
    with mock.patch.dict(os.environ, {"EXTRALIT_AUTH_SECRET_KEY": secret_key}):
        settings = Settings()

        assert settings.secret_key == secret_key


def test_configure_oauth_cfg():
    oauth_cfg = "mock-oauth-cfg"
    with mock.patch.dict(os.environ, {"EXTRALIT_AUTH_OAUTH_CFG": oauth_cfg}):
        settings = Settings()

        assert settings.oauth_cfg == oauth_cfg


def test_configure_oauth_with_none_allowed_workspaces():
    with tempfile.NamedTemporaryFile(mode="wt") as file:
        file.writelines(["allowed_workspaces:", ""])
        file.flush()

        with mock.patch.dict(os.environ, {"EXTRALIT_AUTH_OAUTH_CFG": file.name}):
            settings = Settings()

            assert settings.oauth.allowed_workspaces == []
