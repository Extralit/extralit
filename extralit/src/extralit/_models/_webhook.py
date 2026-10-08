from enum import Enum
from typing import Optional

from pydantic import ConfigDict, Field

from extralit._models._base import ResourceModel


class EventType(str, Enum):
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

    @property
    def resource(self) -> str:
        """
        Get the instance type of the event.

        Returns:
            str: The instance type. It can be "dataset", "record", or "response".

        """
        return self.split(".")[0]

    @property
    def action(self) -> str:
        """
        Get the action type of the event.

        Returns:
            str: The action type. It can be "created", "updated", "deleted", "published",  or "completed".

        """
        return self.split(".")[1]


class WebhookModel(ResourceModel):
    url: str
    events: list[EventType]
    enabled: bool = True
    description: Optional[str] = None

    secret: Optional[str] = Field(None, description="Webhook secret. Read-only.")

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
    )
