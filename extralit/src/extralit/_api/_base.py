from typing import TYPE_CHECKING, Generic, TypeVar
from uuid import UUID

from extralit._helpers import LoggingMixin

if TYPE_CHECKING:
    from httpx import Client

__all__ = ["ResourceAPI"]

T = TypeVar("T")


# TODO: Use ABC and align all the abstract method for the different resources APIs
# See comment https://github.com/argilla-io/argilla-python/pull/33#discussion_r1532079989
class ResourceAPI(LoggingMixin, Generic[T]):
    """Base class for all API resources that contains common methods."""

    def __init__(self, http_client: "Client") -> None:
        self.http_client = http_client

    ################
    # CRUD methods #
    ################

    def get(self, id: UUID) -> T:
        raise NotImplementedError

    def create(self, resource: T) -> T:
        raise NotImplementedError

    def delete(self, id: UUID) -> None:
        raise NotImplementedError

    def update(self, resource: T) -> T:
        return resource
