import os

from pydantic import BaseModel, Field

MIN_MESSAGE_LENGTH = int(os.getenv("EXTRALIT_MIN_MESSAGE_LENGTH", 1))
MAX_MESSAGE_LENGTH = int(os.getenv("EXTRALIT_MAX_MESSAGE_LENGTH", 20000))

MIN_ROLE_LENGTH = int(os.getenv("EXTRALIT_MIN_ROLE_LENGTH", 1))
MAX_ROLE_LENGTH = int(os.getenv("EXTRALIT_MAX_ROLE_LENGTH", 20))


class ChatFieldValue(BaseModel):
    role: str = Field(..., min_length=MIN_ROLE_LENGTH, max_length=MAX_ROLE_LENGTH)
    content: str = Field(..., min_length=MIN_MESSAGE_LENGTH, max_length=MAX_MESSAGE_LENGTH)
