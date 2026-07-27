from extralit_server._app import create_server_app


class TestApiMounts:
    def test_only_v1_is_mounted(self):
        app = create_server_app()
        mounts = {route.path for route in app.routes if hasattr(route, "app")}
        assert "/api/v1" in mounts
        assert "/api/v2" not in mounts
