from typing import Generic, TypeVar

__all__ = ["GenericIterator"]

Item = TypeVar("Item")


class GenericIterator(Generic[Item]):
    """Generic iterator for any collection of items."""

    def __init__(self, collection: list[Item]):
        self._collection = list(collection)
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index < len(self._collection):
            result = self._collection[self._index]
            self._index += 1
            return result
        raise StopIteration
