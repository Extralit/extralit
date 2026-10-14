from typing import Any

from extralit_server.pydantic_v1 import BaseModel, root_validator


class UpdateSchema(BaseModel):
    """Base schema for update endpoints. `__non_nullable_fields__` is a set of fields that cannot be set to `None`
    explicitly. The list of fields is validated in `validate_non_nullable_fields` root validator, which will raise a
    `ValueError` if any of the fields in the set was set to `None` explicitly.
    """

    __non_nullable_fields__: set[str] | None = None

    @root_validator(pre=True)
    def validate_non_nullable_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        if cls.__non_nullable_fields__ is None:
            return values

        invalid_keys = []
        for key in cls.__non_nullable_fields__:
            if key in values and values[key] is None:
                invalid_keys.append(key)

        if invalid_keys:
            raise ValueError(f"The following keys must have non-null values: {', '.join(invalid_keys)}")

        return values
