from starlette.routing import Mount

from extralit_server._app import app


class TestApiMounts:
    def test_only_v1_is_mounted(self):
        # Assert against the module-level app rather than calling create_server_app():
        # the factory returns a *wrapper* app when settings.base_url != "/", and it runs
        # configure_app_statics, which copytree's the bundled frontend into a temp dir.
        mounts = {route.path for route in app.routes if isinstance(route, Mount)}
        assert "/api/v1" in mounts
        assert "/api/v2" not in mounts
