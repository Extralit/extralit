from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from extralit_server.enums import MetadataPropertyType
from extralit_server.errors.future import UnprocessableEntityError

__all__ = [
    "FloatMetadataPropertySettings",
    "IntegerMetadataPropertySettings",
    "MetadataPropertySettings",
    "TermsMetadataPropertySettings",
]

try:
    from typing import Annotated
except ImportError:
    from typing import Annotated


class BaseMetadataPropertySettings(BaseModel, ABC):
    @abstractmethod
    def check_metadata(self, value: Any) -> None:
        pass


class TermsMetadataPropertySettings(BaseMetadataPropertySettings):
    type: Literal[MetadataPropertyType.terms]
    values: list[Any] | None = None

    def check_metadata(self, value: Any) -> None:
        if self.values is None:
            return

        values = value
        if not isinstance(values, list):
            values = [value]

        for v in values:
            if v not in self.values:
                raise UnprocessableEntityError(f"'{v}' is not an allowed term.")


NT = TypeVar("NT", int, float)


class NumericMetadataPropertySettings(BaseMetadataPropertySettings, BaseModel, Generic[NT]):
    min: NT | None = None
    max: NT | None = None

    def check_metadata(self, value: NT) -> None:
        if self.min is not None and value < self.min:
            raise UnprocessableEntityError(f"'{value}' is less than the minimum value of '{self.min}'.")

        if self.max is not None and value > self.max:
            raise UnprocessableEntityError(f"'{value}' is greater than the maximum value of '{self.max}'.")


class IntegerMetadataPropertySettings(NumericMetadataPropertySettings[int]):
    type: Literal[MetadataPropertyType.integer]

    def check_metadata(self, value: int) -> None:
        if not isinstance(value, int):
            raise UnprocessableEntityError(f"'{value}' is not an integer.")

        return super().check_metadata(value)


class FloatMetadataPropertySettings(NumericMetadataPropertySettings[float]):
    type: Literal[MetadataPropertyType.float]

    def check_metadata(self, value: float) -> None:
        if not isinstance(value, float):
            raise UnprocessableEntityError(f"'{value}' is not a float.")

        return super().check_metadata(value)


MetadataPropertySettings = Annotated[
    TermsMetadataPropertySettings | IntegerMetadataPropertySettings | FloatMetadataPropertySettings,
    Field(..., discriminator="type"),
]
