from fastapi import Request
from starlette.routing import Mount, Route


def resolve_endpoint_path_for_request(request: Request) -> str | None:
    """
    Resolves the configured route endpoint path for the incoming request

    Parameters:
        request (Request): The incoming request

    Returns:
        The route path for the incoming request. None if the route path cannot be resolved.
    """

    all_routes = request.scope.get("router").routes or []

    for route in all_routes:
        parent = None
        routes: list[Route] = [route]

        if isinstance(route, Mount):
            parent = route
            routes = [route for route in route.routes if isinstance(route, Route)]

        for route in routes:
            if route.endpoint == request.scope.get("endpoint"):
                route_path = route.path
                if parent:
                    route_path = f"{parent.path}{route_path}"

                return route_path
