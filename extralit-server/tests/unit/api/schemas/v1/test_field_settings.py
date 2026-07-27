import pytest
from pydantic import TypeAdapter, ValidationError

from extralit_server.api.schemas.v1.fields import FieldSettings, FieldSettingsCreate


class TestColumnFieldSettings:
    def test_column_settings_parse_from_the_discriminated_union(self):
        settings = TypeAdapter(FieldSettings).validate_python({"type": "column", "dtype": "int64", "nullable": False})
        assert settings.type == "column"
        assert settings.dtype == "int64"
        assert settings.nullable is False
        assert settings.review is None

    def test_column_settings_default_to_nullable_with_no_review_overlay(self):
        settings = TypeAdapter(FieldSettingsCreate).validate_python({"type": "column", "dtype": "string"})
        assert settings.nullable is True
        assert settings.review is None

    def test_column_settings_carry_an_opaque_review_overlay(self):
        settings = TypeAdapter(FieldSettings).validate_python(
            {"type": "column", "dtype": "string", "review": {"widget": "textarea", "rows": 4}}
        )
        assert settings.review == {"widget": "textarea", "rows": 4}

    def test_column_settings_require_a_dtype(self):
        with pytest.raises(ValidationError):
            TypeAdapter(FieldSettings).validate_python({"type": "column"})
