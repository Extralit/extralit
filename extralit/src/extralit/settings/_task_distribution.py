# from typing import Literal, Any, Dict
from typing import Any, Literal

from extralit._models._settings._task_distribution import OverlapTaskDistributionModel


class OverlapTaskDistribution:
    """The task distribution settings class.

    This task distribution defines a number of submitted responses required to complete a record.

    Parameters:
        min_submitted (int): The number of min. submitted responses to complete the record
    """

    strategy: Literal["overlap"] = "overlap"

    def __init__(self, min_submitted: int):
        self._model = OverlapTaskDistributionModel(min_submitted=min_submitted, strategy=self.strategy)

    def __repr__(self) -> str:
        return f"OverlapTaskDistribution(min_submitted={self.min_submitted})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self._model == other._model

    @classmethod
    def default(cls) -> "OverlapTaskDistribution":
        return cls(min_submitted=1)

    @property
    def min_submitted(self):
        return self._model.min_submitted

    @min_submitted.setter
    def min_submitted(self, value: int):
        self._model.min_submitted = value

    @classmethod
    def from_model(cls, model: OverlapTaskDistributionModel) -> "OverlapTaskDistribution":
        return cls(min_submitted=model.min_submitted)

    @classmethod
    def from_dict(cls, dict: dict[str, Any]) -> "OverlapTaskDistribution":
        return cls.from_model(OverlapTaskDistributionModel.model_validate(dict))

    def to_dict(self):
        return self._model.model_dump()

    def _api_model(self) -> OverlapTaskDistributionModel:
        return self._model


TaskDistribution = OverlapTaskDistribution
