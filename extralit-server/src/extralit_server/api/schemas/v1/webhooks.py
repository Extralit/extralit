# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator

from extralit_server.api.schemas.v1.commons import UpdateSchema
from extralit_server.webhooks.v1.enums import WebhookEvent

WEBHOOK_EVENTS_MIN_ITEMS = 1
WEBHOOK_DESCRIPTION_MIN_LENGTH = 1
WEBHOOK_DESCRIPTION_MAX_LENGTH = 1000


class Webhook(BaseModel):
    id: UUID
    url: str
    secret: str
    events: list[WebhookEvent]
    enabled: bool
    description: str | None = None
    inserted_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Webhooks(BaseModel):
    items: list[Webhook]


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[WebhookEvent] = Field(min_length=WEBHOOK_EVENTS_MIN_ITEMS)
    description: str | None = Field(
        None,
        min_length=WEBHOOK_DESCRIPTION_MIN_LENGTH,
        max_length=WEBHOOK_DESCRIPTION_MAX_LENGTH,
    )

    @field_validator("events")
    @classmethod
    def events_must_be_unique(cls, events: list[WebhookEvent]):
        if len(set(events)) != len(events):
            raise ValueError("Events must be unique")

        return events

    @field_serializer("url")
    def serialize_url(self, url: HttpUrl):
        return str(url)


class WebhookUpdate(UpdateSchema):
    url: HttpUrl | None = None
    events: list[WebhookEvent] | None = Field(None, min_length=WEBHOOK_EVENTS_MIN_ITEMS)
    enabled: bool | None = None
    description: str | None = Field(
        None,
        min_length=WEBHOOK_DESCRIPTION_MIN_LENGTH,
        max_length=WEBHOOK_DESCRIPTION_MAX_LENGTH,
    )

    __non_nullable_fields__ = {"url", "events", "enabled"}

    @field_validator("events")
    @classmethod
    def events_must_be_unique(cls, events: list[WebhookEvent] | None):
        if events is None:
            return

        if len(set(events)) != len(events):
            raise ValueError("Events must be unique")

        return events

    @field_serializer("url")
    def serialize_url(self, url: HttpUrl | None):
        if url is None:
            return

        return str(url)
