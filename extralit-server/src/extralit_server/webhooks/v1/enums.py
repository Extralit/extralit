try:
    from enum import StrEnum
except ImportError:
    from extralit_server.utils.str_enum import StrEnum


class WebhookEvent(StrEnum):
    dataset_created = "dataset.created"
    dataset_updated = "dataset.updated"
    dataset_deleted = "dataset.deleted"
    dataset_published = "dataset.published"

    record_created = "record.created"
    record_updated = "record.updated"
    record_deleted = "record.deleted"
    record_completed = "record.completed"

    response_created = "response.created"
    response_updated = "response.updated"
    response_deleted = "response.deleted"


class DatasetEvent(StrEnum):
    created = WebhookEvent.dataset_created.value
    updated = WebhookEvent.dataset_updated.value
    deleted = WebhookEvent.dataset_deleted.value
    published = WebhookEvent.dataset_published.value


class RecordEvent(StrEnum):
    created = WebhookEvent.record_created.value
    updated = WebhookEvent.record_updated.value
    deleted = WebhookEvent.record_deleted.value
    completed = WebhookEvent.record_completed.value


class ResponseEvent(StrEnum):
    created = WebhookEvent.response_created.value
    updated = WebhookEvent.response_updated.value
    deleted = WebhookEvent.response_deleted.value
