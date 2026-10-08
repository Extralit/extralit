from pydantic import BaseModel


class Version(BaseModel):
    version: str


class Status(BaseModel):
    version: str
    search_engine: dict
    memory: dict
