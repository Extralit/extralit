import pytest

import extralit as ex


class TestTextField:
    def test_init_text_field(self):
        mock_name = "prompt"
        mock_use_markdown = True
        text_field = ex.TextField(name=mock_name, use_markdown=mock_use_markdown)
        assert text_field.name == mock_name
        assert text_field.use_markdown == mock_use_markdown
        assert text_field.title == mock_name
        assert text_field.required is True

    def test_init_text_field_with_title(self):
        mock_name = "prompt"
        mock_use_markdown = True
        mock_title = "Prompt"
        text_field = ex.TextField(name=mock_name, use_markdown=mock_use_markdown, title=mock_title)
        assert text_field.name == mock_name
        assert text_field.use_markdown == mock_use_markdown
        assert text_field.title == mock_title
        assert text_field.required is True

    @pytest.mark.parametrize(
        "title, name, expected",
        [
            (None, "prompt", "prompt"),
            ("Prompt", "prompt", "Prompt"),
            ("Prompt", "prompt", "Prompt"),
        ],
    )
    def test_title_validator(self, title, name, expected, mocker):
        mock_use_markdown = True
        text_field = ex.TextField(name=name, use_markdown=mock_use_markdown, title=title)
        assert text_field.title == expected


class TestChatField:
    def test_create_chat_field(self):
        field = ex.ChatField(name="chat")

        assert field.name == "chat"
        assert field.use_markdown is True

    def test_create_chat_field_with_use_markdown(self):
        field = ex.ChatField(name="chat", use_markdown=False)

        assert field.name == "chat"
        assert field.use_markdown is False

    def test_update_chat_field_use_markdown(self):
        field = ex.ChatField(name="chat", use_markdown=True)
        field.use_markdown = False

        assert field.use_markdown is False


class TestCustomField:
    def test_create_custom_field(self):
        field = ex.CustomField(name="custom", template="<p>{{ custom }}</p>")

        assert field.name == "custom"
        assert field.template == "<p>{{ custom }}</p>"
        assert field.advanced_mode is False

    def test_create_custom_field_with_advanced_mode(self):
        field = ex.CustomField(name="custom", template="<p></p>", advanced_mode=True)

        assert field.name == "custom"
        assert field.template == "<p></p>"
        assert field.advanced_mode is True
