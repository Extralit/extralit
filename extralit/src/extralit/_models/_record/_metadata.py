from typing import Annotated, Any

from pydantic import BaseModel


class MetadataModel(BaseModel):
    """Schema for the metadata of a `Dataset`"""

    name: Annotated[str, "The name of the metadata field or key in the metadata dictionary"]
    value: Any
