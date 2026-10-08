from typing import Any

from pydantic import BaseModel, model_validator


class UpdateSchema(BaseModel):
    """Base schema for update endpoints. `__non_nullable_fields__` is a set of fields that cannot be set to `None`
    explicitly. The list of fields is validated in `validate_non_nullable_fields` root validator, which will raise a
    `ValueError` if any of the fields in the set was set to `None` explicitly.
    """

    __non_nullable_fields__: set[str] | None = None

    @model_validator(mode="before")
    @classmethod
    def validate_non_nullable_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
        if cls.__non_nullable_fields__ is None:
            return data

        invalid_keys = []
        for key in cls.__non_nullable_fields__:
            if key in data and data[key] is None:
                invalid_keys.append(key)

        if invalid_keys:
            raise ValueError(f"The following keys must have non-null values: {', '.join(invalid_keys)}")

        return data
