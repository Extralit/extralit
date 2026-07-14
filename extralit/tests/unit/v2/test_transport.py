import pytest

from extralit.v2._api._errors import AuthError, NotFoundError, ValidationError
from extralit.v2._api._transport import AsyncTransport

pytestmark = pytest.mark.asyncio

API = "http://test:6900"


async def test_api_key_header_sent(httpx_mock):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", json={"items": []})
    t = AsyncTransport(API, api_key="secret.key")
    body = await t.request("GET", "/schemas", params={"workspace_id": "w1"})
    assert body == {"items": []}
    assert httpx_mock.get_requests()[0].headers["X-Extralit-Api-Key"] == "secret.key"
    await t.aclose()


async def test_password_login_then_bearer(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{API}/api/v2/token",
        status_code=201,
        json={"access_token": "AT1", "refresh_token": "RT1"},
    )
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", json={"items": []})
    t = AsyncTransport(API, username="u", password="p")
    await t.request("GET", "/schemas", params={"workspace_id": "w1"})
    token_req, api_req = httpx_mock.get_requests()
    assert b"username=u" in token_req.content and b"password=p" in token_req.content
    assert api_req.headers["Authorization"] == "Bearer AT1"
    await t.aclose()


async def test_refresh_once_on_401_then_retry(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{API}/api/v2/token",
        status_code=201,
        json={"access_token": "AT1", "refresh_token": "RT1"},
    )
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", status_code=401, json={"detail": "expired"})
    httpx_mock.add_response(
        method="POST",
        url=f"{API}/api/v2/token/refresh",
        status_code=201,
        json={"access_token": "AT2", "refresh_token": "RT2"},
    )
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", json={"items": []})
    t = AsyncTransport(API, username="u", password="p")
    body = await t.request("GET", "/schemas", params={"workspace_id": "w1"})
    assert body == {"items": []}
    refresh_req = httpx_mock.get_requests()[2]
    assert b"RT1" in refresh_req.content
    assert httpx_mock.get_requests()[3].headers["Authorization"] == "Bearer AT2"
    await t.aclose()


async def test_401_after_failed_refresh_raises_auth_error(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url=f"{API}/api/v2/token",
        status_code=201,
        json={"access_token": "AT1", "refresh_token": "RT1"},
    )
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", status_code=401, json={"detail": "expired"})
    httpx_mock.add_response(method="POST", url=f"{API}/api/v2/token/refresh", status_code=401, json={"detail": "no"})
    t = AsyncTransport(API, username="u", password="p")
    with pytest.raises(AuthError):
        await t.request("GET", "/schemas", params={"workspace_id": "w1"})
    await t.aclose()


async def test_api_key_401_raises_without_refresh(httpx_mock):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w1", status_code=401, json={"detail": "bad key"})
    t = AsyncTransport(API, api_key="bad")
    with pytest.raises(AuthError):
        await t.request("GET", "/schemas", params={"workspace_id": "w1"})
    assert len(httpx_mock.get_requests()) == 1  # no refresh attempt in api-key mode
    await t.aclose()


async def test_error_mapping_and_204(httpx_mock):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/x", status_code=404, json={"detail": "gone"})
    httpx_mock.add_response(method="POST", url=f"{API}/api/v2/schemas", status_code=422, json={"detail": "bad"})
    httpx_mock.add_response(method="DELETE", url=f"{API}/api/v2/schemas/y/records?ids=a", status_code=204)
    t = AsyncTransport(API, api_key="k")
    with pytest.raises(NotFoundError):
        await t.request("GET", "/schemas/x")
    with pytest.raises(ValidationError):
        await t.request("POST", "/schemas", json={})
    assert await t.request("DELETE", "/schemas/y/records", params={"ids": "a"}) is None
    await t.aclose()
