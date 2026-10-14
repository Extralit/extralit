from dataclasses import dataclass, fields
from typing import TypeVar

__all__ = ["dataclass_instance_from_dict"]

T = TypeVar("T", bound=dataclass)


def dataclass_instance_from_dict(cls: type[T], data: dict) -> T:
    """Create a dataclass instance from a dictionary, ignoring extra keys found in the dictionary."""

    field_names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in field_names})
