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

from uuid import UUID

from extralit_server.api.policies.v1.commons import PolicyAction
from extralit_server.models import User


class DocumentPolicy:
    @classmethod
    def create(cls) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or actor.is_admin or actor.is_annotator

        return is_allowed

    @classmethod
    def get(cls) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            # TODO check if the user has access to the workspace
            return actor.is_owner or actor.is_admin or actor.is_annotator

        return is_allowed

    @classmethod
    def bulk_create(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed

    @classmethod
    def delete(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed

    @classmethod
    def list(cls, workspace_id: UUID) -> PolicyAction:
        async def is_allowed(actor: User) -> bool:
            return actor.is_owner or (actor.is_admin and await actor.is_member(workspace_id))

        return is_allowed
