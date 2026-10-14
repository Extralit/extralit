from uuid import UUID

from extralit_server.api.schemas.v1.suggestions import SuggestionCreate


class SuggestionCreateWithRecordId(SuggestionCreate):
    record_id: UUID
