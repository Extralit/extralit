from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.errors.future import NotUniqueError, UnprocessableEntityError
from extralit_server.models import User


class UserCreateValidator:
    @classmethod
    async def validate(cls, db: AsyncSession, user: User) -> None:
        await cls._validate_username(db, user)
        await cls._validate_user_id(db, user)

    @classmethod
    async def _validate_username(cls, db, user: User):
        await cls._validate_username_length(user)
        await cls._validate_unique_username(db, user)

    @classmethod
    async def _validate_unique_username(cls, db, user):
        from extralit_server.contexts import accounts

        if await accounts.get_user_by_username(db, user.username) is not None:
            raise NotUniqueError(f"User username `{user.username}` is not unique")

    @classmethod
    async def _validate_username_length(cls, user: User):
        if len(user.username) < 1:
            raise UnprocessableEntityError("Username must be at least 1 characters long")

    @classmethod
    async def _validate_user_id(cls, db, user: User):
        if user.id is None:
            return

        if await User.get(db, id=user.id) is not None:
            raise NotUniqueError(f"User with id `{user.id}` is not unique")
