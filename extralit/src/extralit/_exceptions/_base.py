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
from typing import Optional


class ExtralitError(Exception):
    message_stub = "Extralit SDK error"

    def __init__(self, message: Optional[str] = None):
        """Base class for all Extralit exceptions
        Args:
            message (str): The message to display when the exception is raised
        """
        super().__init__(message or self.message_stub)

    def __str__(self):
        return f"{self.message_stub}: {self.__class__.__name__}: {super().__str__()}"

    def __repr__(self):
        return f"{self.message_stub}: {self.__class__.__name__}: {super().__repr__()}"
