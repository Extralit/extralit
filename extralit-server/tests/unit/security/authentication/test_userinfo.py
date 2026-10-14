import os

from pytest_mock import MockerFixture

from extralit_server.enums import UserRole
from extralit_server.security.authentication import UserInfo


class TestUserInfo:
    def test_get_user_name_without_claims(self):
        userinfo = UserInfo()
        assert userinfo.username == ""

    def test_get_userinfo_first_name(self):
        userinfo = UserInfo({"username": "user", "first_name": "User"})
        assert userinfo.first_name == "User"

    def test_get_default_userinfo_first_name(self):
        userinfo = UserInfo({"username": "user"})
        assert userinfo.first_name == "user"

    def test_get_default_userinfo_role(self):
        userinfo = UserInfo({"username": "user"})
        assert userinfo.role == UserRole.annotator

    def test_get_userinfo_role(self):
        userinfo = UserInfo({"username": "user", "role": "owner"})
        assert userinfo.role == UserRole.owner

    def test_get_userinfo_role_with_username_env(self, mocker: MockerFixture):
        mocker.patch.dict(os.environ, {"USERNAME": "user"})

        userinfo = UserInfo({"username": "user"})
        assert userinfo.role == UserRole.owner
