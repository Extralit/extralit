from collections.abc import Awaitable, Callable

from extralit_server.errors import ForbiddenOperationError
from extralit_server.models import User

PolicyAction = Callable[[User], Awaitable[bool]]


async def authorize(actor: User, policy_action: PolicyAction) -> None:
    if not await is_authorized(actor, policy_action):
        raise ForbiddenOperationError()


async def is_authorized(actor: User, policy_action: PolicyAction) -> bool:
    return await policy_action(actor)
