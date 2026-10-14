from pydantic import BaseModel, ConfigDict


class HuggingfaceSettings(BaseModel):
    space_id: str | None
    space_title: str | None
    space_subdomain: str | None
    space_host: str | None
    space_repo_name: str | None
    space_author_name: str | None
    space_persistent_storage_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ExtralitSettings(BaseModel):
    show_huggingface_space_persistent_storage_warning: bool | None = None
    share_your_progress_enabled: bool = False


class Settings(BaseModel):
    extralit: ExtralitSettings
    huggingface: HuggingfaceSettings | None = None
