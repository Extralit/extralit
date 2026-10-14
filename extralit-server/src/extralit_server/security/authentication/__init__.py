from .jwt import JWT
from .provider import AuthenticationProvider
from .userinfo import UserInfo

auth = AuthenticationProvider.new_instance()
