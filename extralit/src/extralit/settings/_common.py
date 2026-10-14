from typing import Any, Optional, Union

from extralit._models import FieldModel, QuestionModel
from extralit._resource import Resource

__all__ = ["SettingsPropertyBase"]


class SettingsPropertyBase(Resource):
    """Base class for dataset fields or questions in Settings class"""

    _model: Union[FieldModel, QuestionModel]

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name={self.name}, title={self.title}, description={self.description}, "
            f"type={self.type}, required={self.required}) \n"
        )

    @property
    def name(self) -> str:
        return self._model.name

    @property
    def title(self) -> Optional[str]:
        return self._model.title

    @title.setter
    def title(self, value: str):
        self._model.title = value

    @property
    def required(self) -> bool:
        return self._model.required

    @required.setter
    def required(self, value: bool):
        self._model.required = value

    @property
    def description(self) -> Optional[str]:
        return self._model.description

    @description.setter
    def description(self, value: str):
        self._model.description = value

    @property
    def type(self) -> str:
        return self._model.settings.type

    def validate(self):
        pass

    def serialize(self) -> dict[str, Any]:
        serialized_model = super().serialize()
        serialized_model["type"] = self.type
        return serialized_model
