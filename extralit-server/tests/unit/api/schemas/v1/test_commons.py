import pytest

from extralit_server.api.schemas.v1.commons import UpdateSchema


def test_update_schema():
    class UnitTestUpdateSchema(UpdateSchema):
        unit: str | None
        test: bool | None

        __non_nullable_fields__ = {"unit", "test"}

    with pytest.raises(ValueError):
        UnitTestUpdateSchema(unit=None, test=None)
