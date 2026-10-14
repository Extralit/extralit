import warnings
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_serializer, field_validator


class ResponseStatus(str, Enum):
    draft = "draft"
    submitted = "submitted"
    discarded = "discarded"


class UserResponseModel(BaseModel):
    """Schema for the `FeedbackRecord` user response."""

    values: Union[dict[str, dict[str, Any]], None]
    status: ResponseStatus
    user_id: Optional[UUID] = Field(None, validate_default=True)

    class Config:
        validate_assignment = True

    @field_validator("user_id")
    @classmethod
    def user_id_must_have_value(cls, user_id: Optional[UUID]):
        if not user_id:
            warnings.warn(
                "`user_id` not provided, so it will be set to `None`. Which is not an"
                " issue, unless you're planning to log the response in Extralit, as"
                " it will be automatically set to the active `user_id`.",
                stacklevel=2,
            )
        return user_id

    @field_serializer("user_id", when_used="always")
    def serialize_user_id(value: UUID) -> str:
        return str(value)
