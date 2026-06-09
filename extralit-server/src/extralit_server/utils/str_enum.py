from enum import Enum


class StrEnum(str, Enum):
    """Custom StrEnum class for Python <3.11 compatibility."""

    def __str__(self):
        return str(self.value)
