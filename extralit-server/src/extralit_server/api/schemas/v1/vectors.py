from uuid import UUID

from pydantic import BaseModel


class Vector(BaseModel):
    record_id: UUID
    vector_settings_id: UUID
    value: list[float]
