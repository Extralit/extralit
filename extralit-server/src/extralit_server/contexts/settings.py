from extralit_server.api.schemas.v1.settings import ExtralitSettings, HuggingfaceSettings, Settings
from extralit_server.integrations.huggingface.spaces import HUGGINGFACE_SETTINGS
from extralit_server.settings import settings


def get_settings() -> Settings:
    return Settings(
        extralit=_get_extralit_settings(),
        huggingface=_get_huggingface_settings(),
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
