import pytest
from pydantic import TypeAdapter, ValidationError

from extralit_server.api.schemas.v1.fields import (
    ColumnFieldSettingsUpdate,
    FieldSettings,
    FieldSettingsCreate,
    FieldSettingsUpdate,
)


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


class TestColumnFieldSettingsUpdate:
    def test_column_settings_update_allows_a_dtype_only_partial_update(self):
        settings = TypeAdapter(FieldSettingsUpdate).validate_python({"type": "column", "dtype": "int64"})
        assert isinstance(settings, ColumnFieldSettingsUpdate)
        assert settings.dtype == "int64"
        assert settings.nullable is None
        assert settings.review is None

    def test_column_settings_update_allows_a_review_only_partial_update(self):
        settings = TypeAdapter(FieldSettingsUpdate).validate_python(
            {"type": "column", "review": {"widget": "textarea", "rows": 4}}
        )
        assert isinstance(settings, ColumnFieldSettingsUpdate)
        assert settings.dtype is None
        assert settings.nullable is None
        assert settings.review == {"widget": "textarea", "rows": 4}

    def test_column_settings_update_rejects_an_explicit_null_dtype(self):
        with pytest.raises(ValidationError):
            TypeAdapter(FieldSettingsUpdate).validate_python({"type": "column", "dtype": None})

    def test_column_settings_update_rejects_an_explicit_null_nullable(self):
        # `ColumnFieldSettings.nullable: bool = True` is non-Optional. Without `nullable` in
        # `__non_nullable_fields__`, a PATCH body of {"type": "column", "nullable": null} would
        # pass this schema, then `Field.fill()` (models/mixins.py:41-52) dict-merges
        # `nullable: None` into the stored settings JSON — and every subsequent parse of that
        # field via `Field.settings: FieldSettings` would then raise `ValidationError`.
        with pytest.raises(ValidationError):
            TypeAdapter(FieldSettingsUpdate).validate_python({"type": "column", "nullable": None})
