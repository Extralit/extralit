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


from extralit_server.api.schemas.v1.settings import ExtralitSettings, HuggingfaceSettings, OAuthProvider, Settings
from extralit_server.integrations.huggingface.spaces import HUGGINGFACE_SETTINGS
from extralit_server.settings import settings


def get_settings() -> Settings:
    return Settings(
        extralit=_get_extralit_settings(),
        huggingface=_get_huggingface_settings(),
        oauth_providers=_get_oauth_providers(),
    )


def _get_extralit_settings() -> ExtralitSettings:
    extralit_settings = ExtralitSettings(share_your_progress_enabled=settings.enable_share_your_progress)

    if _get_huggingface_settings():
        extralit_settings.show_huggingface_space_persistent_storage_warning = (
            settings.show_huggingface_space_persistent_storage_warning
        )

    return extralit_settings


def _get_huggingface_settings() -> HuggingfaceSettings | None:
    if HUGGINGFACE_SETTINGS.is_running_on_huggingface:
        return HuggingfaceSettings.model_validate(HUGGINGFACE_SETTINGS)


def _get_oauth_providers() -> list[OAuthProvider]:
    """Get available OAuth providers from security settings."""
    providers = []

    try:
        # Import here to avoid circular imports
        from extralit_server.security.settings import settings as security_settings

        # Get configured OAuth providers
        for provider_name in security_settings.oauth.providers.keys():
            display_name = _get_provider_display_name(provider_name)
            icon = _get_provider_icon(provider_name)

            providers.append(
                OAuthProvider(
                    name=provider_name,
                    display_name=display_name,
                    enabled=True,  # If it's configured, it's enabled
                    icon=icon,
                )
            )
    except Exception:
        # If security settings are not available or configured, return empty list
        pass

    return providers


def _get_provider_display_name(provider_name: str) -> str:
    """Get user-friendly display name for OAuth provider."""
    display_names = {
        "huggingface": "HuggingFace",
        "extralithub": "Extralit Hub",
        "github": "GitHub",
        "google": "Google",
        "keycloak": "Keycloak",
    }
    return display_names.get(provider_name, provider_name.title())


def _get_provider_icon(provider_name: str) -> str | None:
    """Get icon identifier for OAuth provider."""
    icons = {
        "huggingface": "huggingface",
        "extralithub": "extralit",
        "github": "github",
        "google": "google",
        "keycloak": "keycloak",
    }
    return icons.get(provider_name)
