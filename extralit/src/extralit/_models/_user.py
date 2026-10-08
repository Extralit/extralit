from enum import Enum
from typing import Optional

from pydantic import ConfigDict, field_validator
from pydantic_core.core_schema import ValidationInfo

from extralit._models import ResourceModel

__all__ = ["Role", "UserModel"]


class Role(str, Enum):
    annotator = "annotator"
    admin = "admin"
    owner = "owner"


class UserModel(ResourceModel):
    username: str
    role: Role = Role.annotator

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    @field_validator("first_name")
    @classmethod
    def __validate_first_name(cls, v, info: ValidationInfo):
        """Set first_name to username if not provided"""
        if isinstance(v, str):
            return v
        elif not v:
            return info.data["username"]

    @field_validator("username", mode="before")
    @classmethod
    def __validate_username(cls, username: str):
        """Ensure that the username is not empty"""
        if not username:
            raise ValueError("Username cannot be empty")
        return username
