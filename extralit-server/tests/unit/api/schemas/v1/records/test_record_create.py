import pytest

from extralit_server.api.schemas.v1.chat import ChatFieldValue
from extralit_server.api.schemas.v1.records import RecordCreate


class TestRecordCreate:
    def test_record_create_with_empty_string_field(self):
        record_create = RecordCreate(fields={"field": ""})
        assert record_create.fields == {"field": ""}

    def test_record_create_with_empty_list_field(self):
        record_create = RecordCreate(fields={"field": []})
        assert record_create.fields == {"field": []}

    def test_record_create_with_empty_dict_field(self):
        record_create = RecordCreate(fields={"field": {}})
        assert record_create.fields == {"field": {}}

    def test_record_create_with_none(self):
        record_create = RecordCreate(fields={"field": None})
        assert record_create.fields == {"field": None}

    def test_record_create_with_string_field(self):
        record_create = RecordCreate(fields={"field": "text"})
        assert record_create.fields == {"field": "text"}

    def test_record_create_with_dict_field(self):
        record_create = RecordCreate(fields={"field": {"key": "value"}})
        assert record_create.fields == {"field": {"key": "value"}}

    def test_record_create_with_chat_field_object(self):
        record_create = RecordCreate(
            fields={
                "field": [
                    ChatFieldValue(role="user", content="Hello, how are you?"),
                    ChatFieldValue(role="bot", content="I'm fine, thank you."),
                ]
            }
        )

        assert record_create.fields == {
            "field": [
                ChatFieldValue(role="user", content="Hello, how are you?"),
                ChatFieldValue(role="bot", content="I'm fine, thank you."),
            ]
        }

        assert record_create.fields == {
            "field": [
                ChatFieldValue(role="user", content="Hello, how are you?"),
                ChatFieldValue(role="bot", content="I'm fine, thank you."),
            ]
        }

    def test_record_create_with_chat_field(self):
        record_create = RecordCreate(
            fields={
                "field": [
                    {"role": "user", "content": "Hello, how are you?"},
                    {"role": "bot", "content": "I'm fine, thank you."},
                ]
            }
        )

        assert record_create.fields == {
            "field": [
                ChatFieldValue(role="user", content="Hello, how are you?"),
                ChatFieldValue(role="bot", content="I'm fine, thank you."),
            ]
        }

    @pytest.mark.parametrize(
        "wrong_value",
        [
            {},
            {"role": "user"},
            {"content": "Hello, how are you?"},
            {"wrong": "value"},
            {"role": "user", "other": "Hello, how are you?"},
            {"content": "Hello, how are you?", "other": "user"},
            ["user", "Hello, how are you?"],
        ],
    )
    def test_record_create_with_wrong_chat_field(self, wrong_value: dict):
        with pytest.raises((ValueError, TypeError)):
            RecordCreate(fields={"field": [wrong_value]})

    def test_record_create_with_exceeded_chat_messages(self):
        with pytest.raises(ValueError):
            RecordCreate(
                fields={
                    "field": [
                        {"role": "user", "content": "Hello, how are you?"},
                        {"role": "bot", "content": "I'm fine, thank you."},
                    ]
                    * 1000
                }
            )
