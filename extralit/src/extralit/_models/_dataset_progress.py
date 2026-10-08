from pydantic import BaseModel


class DatasetProgressModel(BaseModel):
    """Dataset progress model."""

    total: int = 0
    completed: int = 0
    pending: int = 0


class RecordResponseDistributionModel(BaseModel):
    """Response distribution model."""

    submitted: int = 0
    draft: int = 0
    discarded: int = 0


class UserProgressModel(BaseModel):
    """User progress model."""

    username: str
    completed: RecordResponseDistributionModel = RecordResponseDistributionModel()
    pending: RecordResponseDistributionModel = RecordResponseDistributionModel()
