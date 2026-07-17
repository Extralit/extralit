import asyncio

from extralit.v2 import Client

API = "http://test:6900"


def test_sync_mirror_calls_through(httpx_mock):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w", json={"items": []})
    with Client(api_url=API, api_key="k") as client:
        assert client.schemas.list("w") == []


def test_sync_client_works_inside_running_loop(httpx_mock):
    """Jupyter simulation: a loop is already running in the calling thread.
    asyncio.run-based facades explode here; the portal must not."""
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w", json={"items": []})

    async def main():
        with Client(api_url=API, api_key="k") as client:
            return client.schemas.list("w")

    assert asyncio.run(main()) == []


def test_non_coroutine_attrs_pass_through(httpx_mock):
    with Client(api_url=API, api_key="k") as client:
        client.questions.invalidate("some-schema")  # sync method on a resource: plain passthrough
