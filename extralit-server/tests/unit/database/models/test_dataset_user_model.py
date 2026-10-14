import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.models import DatasetUser
from tests.factories import DatasetFactory, UserFactory


@pytest.mark.asyncio
class TestDatasetUserModel:
    async def test_create_duplicated_dataset_user(self, db: AsyncSession):
        user = await UserFactory.create()
        dataset = await DatasetFactory.create()

        db.add_all(
            [
                DatasetUser(user_id=user.id, dataset_id=dataset.id),
                DatasetUser(user_id=user.id, dataset_id=dataset.id),
            ]
        )

        with pytest.raises(IntegrityError, match="constraint"):
            await db.commit()
