from pydantic import Field
from pydantic_settings import BaseSettings


class HuggingfaceSettings(BaseSettings):
    space_id: str | None = Field(None, alias="SPACE_ID")
    space_title: str | None = Field(None, alias="SPACE_TITLE")
    space_subdomain: str | None = Field(None, alias="SPACE_SUBDOMAIN")
    space_host: str | None = Field(None, alias="SPACE_HOST")
    space_repo_name: str | None = Field(None, alias="SPACE_REPO_NAME")
    space_author_name: str | None = Field(None, alias="SPACE_AUTHOR_NAME")
    # NOTE: Hugging Face has a typo in their environment variable name,
    # using PERSISTANT instead of PERSISTENT. We will use the correct spelling in our code.
    space_persistent_storage_enabled: bool = Field(False, alias="PERSISTANT_STORAGE_ENABLED")

    @property
    def is_running_on_huggingface(self) -> bool:
        return bool(self.space_id)


HUGGINGFACE_SETTINGS = HuggingfaceSettings()
