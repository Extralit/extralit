import pytest

from extralit_server.api.schemas.v1.users import User, UserCreate
from tests.factories import UserFactory


@pytest.mark.parametrize(
    "username",
    [
        "user-name",
        "user_name",
        "user123",
        "user-123",
        "user_123",
        "UserName",
        "userName",
        "User_name",
        "valid_user_name",
        "user-123_abc",
        "user_123-abc",
        "0033_user",
        "12-user",
    ],
)
def test_user_create(username: str):
    assert UserCreate(first_name="first-name", username=username, password="12345678")


@pytest.mark.asyncio
async def test_user_first_name():
    user = await UserFactory.create(first_name="first-name", workspaces=[])

    assert User.model_validate(user).first_name == "first-name"


@pytest.mark.asyncio
async def test_user_last_name():
    user = await UserFactory.create(last_name="last-name", workspaces=[])

    assert User.model_validate(user).last_name == "last-name"
