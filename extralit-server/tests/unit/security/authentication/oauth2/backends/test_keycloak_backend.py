from extralit_server.security.authentication.oauth2._backends import KeycloakOpenId, Strategy


class TestKeyCloackOpenIdBackend:
    def test_get_user_details_with_extralit_role(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2", "extralit_role:annotator"]},
            }
        )

        assert user_details["role"] == "annotator"

    def test_get_user_details_with_wrong_extralit_role_definition(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2", "extralit_role=annotator"]},
            }
        )

        assert "role" not in user_details

    def test_get_user_details_without_extralit_role(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2"]},
            }
        )

        assert "role" not in user_details

    def test_get_user_details_with_extralit_workspaces(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2", "extralit_workspace:ws1"]},
            }
        )

        assert user_details["available_workspaces"] == ["ws1"]

    def test_get_user_details_with_wrong_extralit_workspace_definition(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2", "extralit_workspace=ws1"]},
            }
        )

        assert "available_workspaces" not in user_details

    def test_get_user_details_with_multiple_extralit_workspaces(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2", "extralit_workspace:ws1", "extralit_workspace:ws2"]},
            }
        )

        assert user_details["available_workspaces"] == ["ws1", "ws2"]

    def test_get_user_details_with_missing_extralit_workspaces(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"roles": ["role1", "role2"]},
            }
        )

        assert "available_workspaces" not in user_details

    def test_get_user_details_with_missing_roles_key(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details(
            {
                "realm_access": {"other": "stuff"},
            }
        )

        assert "role" not in user_details
        assert "available_workspaces" not in user_details

    def test_get_user_details_with_missing_realm_access_key(self):
        backend = KeycloakOpenId(strategy=Strategy())

        user_details = backend.get_user_details({"other": "stuff"})

        assert "role" not in user_details
        assert "available_workspaces" not in user_details
