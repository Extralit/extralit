from fastapi import APIRouter, Request
from fastapi.routing import APIRoute
from starlette.routing import Mount

from extralit_server.utils._fastapi import resolve_endpoint_path_for_request


def mock_endpoint(*args, **kwargs):
    pass


class TestFastAPIUTils:
    def test_resolve_endpoint_path_for_request(self):
        request = Request(
            scope={
                "type": "http",
                "router": APIRouter(routes=[APIRoute(path="/api/endpoint", endpoint=mock_endpoint)]),
                "endpoint": mock_endpoint,
            }
        )

        endpoint_path = resolve_endpoint_path_for_request(request)
        assert endpoint_path == "/api/endpoint"

    def test_resolve_endpoint_path_for_request_with_mount(self):
        request = Request(
            scope={
                "type": "http",
                "router": APIRouter(
                    routes=[Mount(path="/api", routes=[APIRoute(path="/endpoint", endpoint=mock_endpoint)])],
                ),
                "endpoint": mock_endpoint,
            }
        )

        endpoint_path = resolve_endpoint_path_for_request(request)
        assert endpoint_path == "/api/endpoint"

    def test_resolve_endpoint_path_for_request_with_different_endpoint(self):
        request = Request(
            scope={
                "type": "http",
                "router": APIRouter(
                    routes=[APIRoute(path="/api/endpoint", endpoint=mock_endpoint)],
                ),
                "endpoint": lambda x: x,
            }
        )

        endpoint_path = resolve_endpoint_path_for_request(request)
        assert endpoint_path is None

    def test_resolve_endpoint_path_for_request_with_missing_endpoint(self):
        request = Request(
            scope={
                "type": "http",
                "router": APIRouter(
                    routes=[APIRoute(path="/api/endpoint", endpoint=mock_endpoint)],
                ),
            }
        )

        endpoint_path = resolve_endpoint_path_for_request(request)
        assert endpoint_path is None
