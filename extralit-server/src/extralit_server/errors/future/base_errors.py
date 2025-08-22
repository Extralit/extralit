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

__all__ = [
    "AuthenticationError",
    "MissingVectorError",
    "NotFoundError",
    "NotUniqueError",
    "UnprocessableEntityError",
    "UpdateDistributionWithExistingResponsesError",
]

NOT_FOUND_ERROR = "not_found"
NOT_UNIQUE_ERROR = "not_unique"
UNPROCESSABLE_ENTITY_ERROR_CODE = "unprocessable_entity"
MISSING_VECTOR_ERROR_CODE = "missing_vector"
UPDATE_DISTRIBUTION_WITH_EXISTING_RESPONSES_ERROR_CODE = "update_distribution_with_existing_responses"


class NotFoundError(Exception):
    """Custom Extralit not found error. Use it for situations where an Extralit domain entity has not be found on the system."""

    def __init__(self, message, code=NOT_FOUND_ERROR):
        self.message = message
        self.code = code


class NotUniqueError(Exception):
    """Custom Extralit not unique error. Use it for situations where an Extralit domain entity already exists violating a constraint."""

    def __init__(self, message, code=NOT_UNIQUE_ERROR):
        self.message = message
        self.code = code


class UnprocessableEntityError(Exception):
    """Custom Extralit unprocessable entity error. Use it for situations where an Extralit domain entity can not be processed."""

    def __init__(self, message, code=UNPROCESSABLE_ENTITY_ERROR_CODE):
        self.message = message
        self.code = code


# TODO: Once we move to v2.0 we can remove this error and use UnprocessableEntityError
class MissingVectorError(UnprocessableEntityError):
    pass


class UpdateDistributionWithExistingResponsesError(UnprocessableEntityError):
    def __init__(self, message: str):
        super().__init__(message, code=UPDATE_DISTRIBUTION_WITH_EXISTING_RESPONSES_ERROR_CODE)


class AuthenticationError(Exception):
    """Custom Extralit unauthorized error. Use it for situations where an request is not authorized to perform an action."""
