from typing import Any

from extralit._models import VectorModel
from extralit._resource import Resource

__all__ = ["Vector"]


class Vector(Resource):
    """ Class for interacting with Extralit Vectors. Vectors are typically used to represent \
        embeddings or features of records. The `Vector` class is used to deliver vectors to the Extralit server.

    Attributes:
        name (str): The name of the vector.
        values (list[float]): The values of the vector.
    """

    _model: VectorModel

    def __init__(
        self,
        name: str,
        values: list[float],
    ) -> None:
        """Initializes a Vector with a name and values that can be used to search in the Extralit ui.

        Parameters:
            name (str): Name of the vector
            values (list[float]): List of float values

        """
        self._model = VectorModel(
            name=name,
            vector_values=values,
        )

    def __repr__(self) -> str:
        return repr(f"{self.__class__.__name__}({self._model})")

    ##############################
    # Properties
    ##############################

    @property
    def name(self) -> str:
        """Name of the vector that corresponds to the name of the vector in the dataset's `Settings`"""
        return self._model.name

    @property
    def values(self) -> list[float]:
        """List of float values that represent the vector."""
        return self._model.vector_values

    ##############################
    # Methods
    ##############################

    @classmethod
    def from_model(cls, model: VectorModel) -> "Vector":
        return cls(
            name=model.name,
            values=model.vector_values,
        )

    def serialize(self) -> dict[str, Any]:
        dumped_model = self._model.model_dump()
        name = dumped_model.pop("name")
        values = dumped_model.pop("vector_values")
        return {name: values}
