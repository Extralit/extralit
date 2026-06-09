__all__ = ["OverlapTaskDistributionModel", "TaskDistributionModel"]

from typing import Literal

from pydantic import BaseModel, ConfigDict, PositiveInt


class OverlapTaskDistributionModel(BaseModel):
    strategy: Literal["overlap"]
    min_submitted: PositiveInt

    model_config = ConfigDict(validate_assignment=True)


TaskDistributionModel = OverlapTaskDistributionModel
