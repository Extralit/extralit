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
