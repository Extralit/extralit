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

import pytest

from extralit_server.enums import FieldType
from extralit_server.models import Field


@pytest.mark.asyncio
class TestFieldModel:
    def test_is_text_property(self):
        assert Field(settings={"type": FieldType.text}).is_text
        assert not Field(settings={"type": FieldType.image}).is_text
        assert not Field(settings={"type": FieldType.chat}).is_text
        assert not Field(settings={}).is_text

    def test_is_image_property(self):
        assert Field(settings={"type": FieldType.image}).is_image
        assert not Field(settings={"type": FieldType.text}).is_image
        assert not Field(settings={"type": FieldType.chat}).is_image
        assert not Field(settings={}).is_image

    def test_is_chat_property(self):
        assert Field(settings={"type": FieldType.chat}).is_chat
        assert not Field(settings={"type": FieldType.text}).is_chat
        assert not Field(settings={"type": FieldType.image}).is_chat
        assert not Field(settings={}).is_chat
