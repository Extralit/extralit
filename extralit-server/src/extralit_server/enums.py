try:
    from enum import StrEnum
except ImportError:
    from extralit_server.utils.str_enum import StrEnum


class FieldType(StrEnum):
    text = "text"
    image = "image"
    chat = "chat"
    custom = "custom"
    table = "table"


class ResponseStatus(StrEnum):
    draft = "draft"
    submitted = "submitted"
    discarded = "discarded"


class ResponseStatusFilter(StrEnum):
    draft = "draft"
    pending = "pending"
    submitted = "submitted"
    discarded = "discarded"


class SuggestionType(StrEnum):
    model = "model"
    human = "human"
    selection = "selection"


class DatasetStatus(StrEnum):
    draft = "draft"
    ready = "ready"


class DatasetDistributionStrategy(StrEnum):
    overlap = "overlap"


class UserRole(StrEnum):
    owner = "owner"
    admin = "admin"
    annotator = "annotator"


class RecordStatus(StrEnum):
    pending = "pending"
    completed = "completed"


class RecordInclude(StrEnum):
    responses = "responses"
    suggestions = "suggestions"
    vectors = "vectors"
    response_suggestions = "response_suggestions"


class QuestionType(StrEnum):
    text = "text"
    rating = "rating"
    label_selection = "label_selection"
    multi_label_selection = "multi_label_selection"
    ranking = "ranking"
    span = "span"
    table = "table"


class MetadataPropertyType(StrEnum):
    terms = "terms"  # Textual types with a fixed value list
    integer = "integer"  # Integer values
    float = "float"  # Decimal values


class RecordSortField(StrEnum):
    id = "id"
    external_id = "external_id"
    inserted_at = "inserted_at"
    updated_at = "updated_at"
    status = "status"


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class SimilarityOrder(StrEnum):
    most_similar = "most_similar"
    least_similar = "least_similar"


class OptionsOrder(StrEnum):
    natural = "natural"
    suggestion = "suggestion"


class SchemaStatus(StrEnum):
    draft = "draft"
    published = "published"


class V2RecordStatus(StrEnum):
    """v2 record status. Distinct from v1 RecordStatus: adds `discarded` and maps to its
    own PG enum type (v2_record_status_enum) so v1's record_status_enum is untouched."""

    pending = "pending"
    completed = "completed"
    discarded = "discarded"
