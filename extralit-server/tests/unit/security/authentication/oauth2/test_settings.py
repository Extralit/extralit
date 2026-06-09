import pytest

from extralit_server.errors.future import NotFoundError
from extralit_server.security.authentication.oauth2 import OAuth2Settings


class TestOAuth2Settings:
    def test_configure_unsupported_provider(self):
        with pytest.raises(NotFoundError):
            OAuth2Settings(providers=[{"name": "unsupported"}])

    def test_configure_github_provider(self):
        settings = OAuth2Settings(
            providers=[
                {
                    "name": "github",
                    "client_id": "github_client_id",
                    "client_secret": "github_client_secret",
                    "scope": "user:email",
                }
            ]
        )
        github_provider = settings.providers["github"]

        assert github_provider.name == "github"
        assert github_provider.client_id == "github_client_id"
        assert github_provider.client_secret == "github_client_secret"
        assert github_provider.scope == ["user:email"]

    def test_configure_huggingface_provider(self):
        settings = OAuth2Settings(
            providers=[
                {
                    "name": "huggingface",
                    "client_id": "huggingface_client_id",
                    "client_secret": "huggingface_client_secret",
                    "scope": "openid profile email",
                }
            ]
        )
        huggingface_provider = settings.providers["huggingface"]

        assert huggingface_provider.name == "huggingface"
        assert huggingface_provider.client_id == "huggingface_client_id"
        assert huggingface_provider.client_secret == "huggingface_client_secret"
        assert huggingface_provider.scope == ["openid", "profile", "email"]

    def test_configure_extra_backends(self):
        from social_core.backends.microsoft import MicrosoftOAuth2

        provider_name = MicrosoftOAuth2.name
        settings = OAuth2Settings(
            extra_backends=["social_core.backends.microsoft.MicrosoftOAuth2"],
            providers=[
                {
                    "name": provider_name,
                    "client_id": "microsoft_client_id",
                    "client_secret": "microsoft_client_secret",
                }
            ],
        )

        assert len(settings.providers) == 1
        extra_provider = settings.providers[provider_name]

        assert extra_provider.name == provider_name
        assert extra_provider.client_id == "microsoft_client_id"
        assert extra_provider.client_secret == "microsoft_client_secret"

    def test_configure_non_supported_extra_backends(self):
        with pytest.raises(ValueError):
            OAuth2Settings(
                extra_backends=["social_core.backends.twitter.TwitterOAuth"],
                providers=[
                    {
                        "name": "github",
                        "client_id": "github_client_id",
                        "client_secret": "github_client_secret",
                    }
                ],
            )
