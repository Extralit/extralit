import httpx
from httpx import HTTPStatusError

__all__ = ["raise_for_status"]


def raise_for_status(response: httpx.Response) -> None:
    """Raise an exception if the response status code is not a 2xx code."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.is_client_error:
            message = (f"{e.response.json()} {e!r}",)
        else:
            message = f"{e!r}. Response: {e.response.content!r}"

        raise HTTPStatusError(message=message, request=e.request, response=e.response) from e
