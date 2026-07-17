import json

import pytest

from extralit.v2 import AsyncClient

pytestmark = pytest.mark.asyncio

API = "http://test:6900"


async def test_explicit_args_and_resource_wiring(httpx_mock):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w", json={"items": []})
    async with AsyncClient(api_url=API, api_key="k") as client:
        assert await client.schemas.list("w") == []
        for name in ("schemas", "questions", "records", "suggestions", "projections", "responses"):
            assert hasattr(client, name)


async def test_env_fallback(monkeypatch, httpx_mock):
    monkeypatch.setenv("EXTRALIT_API_URL", API)
    monkeypatch.setenv("EXTRALIT_API_KEY", "env-key")
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id=w", json={"items": []})
    async with AsyncClient() as client:
        await client.schemas.list("w")
    assert httpx_mock.get_requests()[0].headers["X-Extralit-Api-Key"] == "env-key"


async def test_credentials_file_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("EXTRALIT_API_URL", raising=False)
    monkeypatch.delenv("EXTRALIT_API_KEY", raising=False)
    creds = tmp_path / "credentials.json"
    creds.write_text(json.dumps({"api_url": API, "api_key": "file-key"}))
    import extralit.client.login as login_mod

    monkeypatch.setattr(login_mod, "EXTRALIT_CREDENTIALS_FILE", creds)
    client = AsyncClient()
    assert client._transport._api_key == "file-key"
    await client.aclose()


async def test_unresolvable_raises(monkeypatch):
    monkeypatch.delenv("EXTRALIT_API_URL", raising=False)
    monkeypatch.delenv("EXTRALIT_API_KEY", raising=False)
    import extralit.client.login as login_mod

    monkeypatch.setattr(login_mod.ExtralitCredentials, "exists", classmethod(lambda cls: False))
    with pytest.raises(ValueError, match="api_url"):
        AsyncClient()
