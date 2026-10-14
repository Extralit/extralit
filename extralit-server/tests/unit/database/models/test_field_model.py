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
