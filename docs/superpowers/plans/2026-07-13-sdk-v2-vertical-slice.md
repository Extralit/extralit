# Python SDK v2 Vertical Slice Implementation Plan

> **Historical note (2026-07-26):** The `/api/v2` parallel tree described in this document was folded back into `/api/v1`. See `docs/superpowers/plans/2026-07-26-fold-v2-into-v1.md`. This document is kept as a historical record; its API paths, models, and file references may no longer exist.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parallel `extralit.v2` SDK package (generated DTOs from the server's `openapi-dump` snapshot, async-native transport + sync facade, five resources for the extraction loop) and top-level agentic CLI verbs (JSON-first) that replace the v1 `schemas` subcommand.

**Architecture:** A new `src/extralit/v2/` package behind a hard import wall (v2 imports nothing from v1 except the credentials helper; only `cli/app.py` — the composition root — imports v2). Wire types are generated from a committed OpenAPI snapshot; hand-written resources form the anti-corruption layer where all wire quirks live; a background-thread event-loop portal gives every async method a mechanical sync mirror.

**Tech Stack:** httpx (AsyncClient), pydantic v2, datamodel-code-generator (dev), typer, pytest + pytest-asyncio (strict mode) + pytest-httpx.

**Spec:** `docs/superpowers/specs/2026-07-13-sdk-v2-redesign-design.md`

## Global Constraints

- All work happens in `extralit/` (the SDK dir of the monorepo). Run commands from `/home/jonny/Projects/Extralit/extralit/extralit/` unless stated otherwise.
- Python floor is `>=3.9.2`: in all v2 source, use `Optional[X]` — never `X | None` — in annotations that pydantic evaluates. Builtin generics (`list[str]`, `dict[str, Any]`) are fine. Put `from __future__ import annotations` at the top of non-model modules only.
- Package management via `uv` only (`uv add`, `uv run pytest`, …). Ruff line length is 120.
- Import wall: files under `src/extralit/v2/` may import stdlib, `httpx`, `pydantic`, `typer`, `rich`, other `extralit.v2.*` modules, and exactly one v1 module: `extralit.client.login` (credentials). No other `extralit.*` import. Outside `v2/`, only `src/extralit/cli/app.py` may import `extralit.v2.*`.
- All wire payloads are typed from `src/extralit/v2/_api/_generated.py`. Never hand-write a wire shape.
- Server caps (mirror, don't re-invent): bulk-upsert ≤ 500 items/request, delete ≤ 100 ids/request, search/list `limit` 1–1000 (default 50).
- Auth endpoints: `POST /api/v2/token` (form `username`/`password`) and `POST /api/v2/token/refresh` (JSON `{"refresh_token": …}`) both return **201** with `{"access_token", "refresh_token"}`. API-key header is `X-Extralit-Api-Key`.
- v2 async tests: pytest-asyncio is in strict mode (no `asyncio_mode` configured) — every async test file needs `pytestmark = pytest.mark.asyncio`.
- Tests live under `tests/unit/v2/`. Commit after every task (pre-commit runs ruff).
- Search/list `total` is approximate (stale index ids skipped; FTS saturates ~10k) — document, never assert exactness in ergonomics.

---

### Task 1: Contract layer — snapshot, codegen, drift gates

**Files:**
- Create: `src/extralit/v2/__init__.py` (placeholder), `src/extralit/v2/_api/__init__.py`, `src/extralit/v2/_api/openapi.json` (generated), `src/extralit/v2/_api/_generated.py` (generated), `tests/unit/v2/__init__.py`, `tests/unit/v2/test_contract.py`
- Modify: `pyproject.toml` (dev dep + ruff exclude)

**Interfaces:**
- Produces: `extralit.v2._api._generated` exporting pydantic v2 models named by the server's OpenAPI components: `SchemaRead`, `Schemas`, `SchemaCreate`, `SchemaUpdate`, `SchemaVersionCreate`, `SchemaVersionRead`, `RecordUpsert`, `RecordsBulkUpsert`, `RecordRead`, `Records`, `RecordFilter`, `RecordSearchQuery`, `ReferenceGroup`, `ReferenceView`, `QuestionCreate`, `QuestionUpdate`, `QuestionRead`, `Questions`, `SuggestionUpsert`, `SuggestionRead`, `Suggestions`, `ResponseUpsert`, `ResponseRead`, `ProjectionCell`, `ProjectionRecord`, `ProjectionView`, and enums `SchemaStatus`, `V2RecordStatus`, `QuestionType`, `SuggestionType`, `ResponseStatus`.

- [ ] **Step 1: Add the codegen dev dependency**

```bash
cd /home/jonny/Projects/Extralit/extralit/extralit
uv add --dev "datamodel-code-generator>=0.26"
```

- [ ] **Step 2: Dump the OpenAPI snapshot from the server tree**

```bash
mkdir -p src/extralit/v2/_api
cd ../extralit-server
uv run python -m extralit_server openapi-dump --output ../extralit/src/extralit/v2/_api/openapi.json
cd ../extralit
python -c "import json; json.load(open('src/extralit/v2/_api/openapi.json'))"  # sanity: valid JSON
```

- [ ] **Step 3: Generate the DTO module**

```bash
uv run datamodel-codegen \
  --input src/extralit/v2/_api/openapi.json \
  --input-file-type openapi \
  --output src/extralit/v2/_api/_generated.py \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.9 \
  --use-double-quotes \
  --disable-timestamp
```

`--disable-timestamp` is load-bearing: the no-drift gate diffs regenerated output byte-for-byte.

- [ ] **Step 4: Exclude the generated file from ruff**

In `pyproject.toml`, extend the `[tool.ruff]` section:

```toml
[tool.ruff]
line-length = 120
extend-exclude = ["src/extralit/v2/_api/_generated.py"]
```

Create the two package inits (empty for now):

```bash
touch src/extralit/v2/__init__.py src/extralit/v2/_api/__init__.py tests/unit/v2/__init__.py
```

- [ ] **Step 5: Write the contract tests**

`tests/unit/v2/test_contract.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

import pytest

SDK_ROOT = Path(__file__).parents[3]
API_DIR = SDK_ROOT / "src" / "extralit" / "v2" / "_api"
SNAPSHOT = API_DIR / "openapi.json"
GENERATED = API_DIR / "_generated.py"
SERVER_DIR = SDK_ROOT.parent / "extralit-server"

EXPECTED_MODELS = [
    "SchemaRead", "Schemas", "SchemaCreate", "SchemaUpdate", "SchemaVersionCreate", "SchemaVersionRead",
    "RecordUpsert", "RecordsBulkUpsert", "RecordRead", "Records", "RecordFilter", "RecordSearchQuery",
    "ReferenceGroup", "ReferenceView",
    "QuestionCreate", "QuestionUpdate", "QuestionRead", "Questions",
    "SuggestionUpsert", "SuggestionRead", "Suggestions", "ResponseUpsert", "ResponseRead",
    "ProjectionCell", "ProjectionRecord", "ProjectionView",
    "SchemaStatus", "V2RecordStatus", "QuestionType", "SuggestionType", "ResponseStatus",
]


def test_generated_models_importable():
    import extralit.v2._api._generated as gen

    missing = [name for name in EXPECTED_MODELS if not hasattr(gen, name)]
    assert not missing, f"generated module lacks: {missing}"


def test_generated_matches_snapshot(tmp_path):
    """No-drift gate: regenerating from the committed snapshot must be byte-identical."""
    out = tmp_path / "regen.py"
    subprocess.run(
        [
            sys.executable, "-m", "datamodel_code_generator",
            "--input", str(SNAPSHOT), "--input-file-type", "openapi",
            "--output", str(out), "--output-model-type", "pydantic_v2.BaseModel",
            "--target-python-version", "3.9", "--use-double-quotes", "--disable-timestamp",
        ],
        check=True, capture_output=True,
    )
    assert out.read_text() == GENERATED.read_text(), (
        "src/extralit/v2/_api/_generated.py drifted from openapi.json — rerun datamodel-codegen (see plan Task 1 Step 3)"
    )


@pytest.mark.slow
@pytest.mark.skipif(not SERVER_DIR.exists(), reason="server tree not present")
def test_snapshot_matches_server():
    """Snapshot-vs-server gate: committed snapshot must equal a fresh openapi-dump."""
    proc = subprocess.run(
        ["uv", "run", "python", "-m", "extralit_server", "openapi-dump"],
        cwd=SERVER_DIR, check=True, capture_output=True, text=True,
    )
    assert json.loads(proc.stdout) == json.loads(SNAPSHOT.read_text()), (
        "openapi.json snapshot drifted from the server — re-dump it (see plan Task 1 Step 2)"
    )
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/unit/v2/test_contract.py -v --disable-warnings
```

Expected: `test_generated_models_importable` and `test_generated_matches_snapshot` PASS; `test_snapshot_matches_server` deselected (slow) — run it once explicitly with `--runslow` and confirm PASS. If `test_generated_models_importable` fails on a name, inspect `_generated.py` for the actual component name and update `EXPECTED_MODELS` *and* note the real name for later tasks (later tasks import these names).

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock src/extralit/v2 tests/unit/v2
git commit -m "feat(sdk-v2): committed OpenAPI snapshot + generated DTOs with drift gates"
```

---

### Task 2: Error hierarchy and 422 normalizer

**Files:**
- Create: `src/extralit/v2/_api/_errors.py`, `tests/unit/v2/test_errors.py`

**Interfaces:**
- Produces:
  - `class V2APIError(Exception)` — attrs `.status_code: int`, `.detail: Any`
  - `class AuthError(V2APIError)`, `class NotFoundError(V2APIError)`
  - `class ValidationError(V2APIError)` — extra attr `.errors: list[dict]` (each `{"loc": list, "msg": str}`)
  - `def error_from_response(status_code: int, body: Any) -> V2APIError`
  - `def normalize_validation_detail(detail: Any) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_errors.py`:

```python
from extralit.v2._api._errors import (
    AuthError,
    NotFoundError,
    V2APIError,
    ValidationError,
    error_from_response,
    normalize_validation_detail,
)


def test_normalizes_string_detail():
    assert normalize_validation_detail("boom") == [{"loc": [], "msg": "boom"}]


def test_normalizes_fastapi_list_detail():
    detail = [{"loc": ["body", "items", 0, "reference"], "msg": "field required", "type": "missing"}]
    assert normalize_validation_detail(detail) == [
        {"loc": ["body", "items", 0, "reference"], "msg": "field required"}
    ]


def test_normalizes_none_and_junk():
    assert normalize_validation_detail(None) == []
    assert normalize_validation_detail({"weird": 1}) == [{"loc": [], "msg": "{'weird': 1}"}]


def test_error_from_response_maps_statuses():
    assert isinstance(error_from_response(401, {"detail": "nope"}), AuthError)
    assert isinstance(error_from_response(403, {"detail": "nope"}), AuthError)
    assert isinstance(error_from_response(404, {"detail": "gone"}), NotFoundError)
    err = error_from_response(422, {"detail": "bad value"})
    assert isinstance(err, ValidationError)
    assert err.errors == [{"loc": [], "msg": "bad value"}]
    other = error_from_response(500, {"detail": "kaboom"})
    assert type(other) is V2APIError
    assert other.status_code == 500 and other.detail == "kaboom"


def test_error_from_response_non_dict_body():
    err = error_from_response(502, "<html>bad gateway</html>")
    assert err.detail == "<html>bad gateway</html>"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_errors.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2._api._errors'`

- [ ] **Step 3: Implement**

`src/extralit/v2/_api/_errors.py`:

```python
from __future__ import annotations

from typing import Any


class V2APIError(Exception):
    """Base error for /api/v2 calls."""

    def __init__(self, status_code: int, detail: Any = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail!r}")


class AuthError(V2APIError):
    """401/403, raised after any transparent token refresh has already been attempted."""


class NotFoundError(V2APIError):
    """404."""


class ValidationError(V2APIError):
    """422. The server emits two body shapes (detail: str | list[{loc, msg}]); `.errors` is normalized."""

    def __init__(self, status_code: int, detail: Any = None):
        super().__init__(status_code, detail)
        self.errors = normalize_validation_detail(detail)


def normalize_validation_detail(detail: Any) -> list[dict]:
    if detail is None:
        return []
    if isinstance(detail, str):
        return [{"loc": [], "msg": detail}]
    if isinstance(detail, list):
        out = []
        for item in detail:
            if isinstance(item, dict):
                out.append({"loc": list(item.get("loc", [])), "msg": str(item.get("msg", item))})
            else:
                out.append({"loc": [], "msg": str(item)})
        return out
    return [{"loc": [], "msg": str(detail)}]


def error_from_response(status_code: int, body: Any) -> V2APIError:
    detail = body.get("detail") if isinstance(body, dict) else body
    if status_code in (401, 403):
        return AuthError(status_code, detail)
    if status_code == 404:
        return NotFoundError(status_code, detail)
    if status_code == 422:
        return ValidationError(status_code, detail)
    return V2APIError(status_code, detail)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_errors.py -v --disable-warnings`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/_api/_errors.py tests/unit/v2/test_errors.py
git commit -m "feat(sdk-v2): error hierarchy with dual-shape 422 normalizer"
```

---

### Task 3: Async transport — auth modes, refresh-once, error mapping

**Files:**
- Create: `src/extralit/v2/_api/_transport.py`, `tests/unit/v2/test_transport.py`

**Interfaces:**
- Consumes: `error_from_response` from Task 2.
- Produces:
  - `class AsyncTransport` — `def __init__(self, api_url: str, api_key: Optional[str] = None, username: Optional[str] = None, password: Optional[str] = None, timeout: float = 60.0, retries: int = 5, extra_headers: Optional[dict] = None)`
  - `async def request(self, method: str, path: str, *, params: Optional[dict] = None, json: Optional[Any] = None) -> Any` — `path` is relative to `/api/v2` (e.g. `"/schemas"`); returns parsed JSON, or `None` for 204/empty bodies. Raises the Task 2 hierarchy on ≥400.
  - `async def aclose(self) -> None`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_transport.py`:

```python
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
        method="POST", url=f"{API}/api/v2/token", status_code=201,
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
        method="POST", url=f"{API}/api/v2/token", status_code=201,
        json={"access_token": "AT1", "refresh_token": "RT1"},
    )
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas?workspace_id=w1", status_code=401, json={"detail": "expired"}
    )
    httpx_mock.add_response(
        method="POST", url=f"{API}/api/v2/token/refresh", status_code=201,
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
        method="POST", url=f"{API}/api/v2/token", status_code=201,
        json={"access_token": "AT1", "refresh_token": "RT1"},
    )
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas?workspace_id=w1", status_code=401, json={"detail": "expired"}
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_transport.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2._api._transport'`

- [ ] **Step 3: Implement**

`src/extralit/v2/_api/_transport.py`:

```python
from __future__ import annotations

from typing import Any, Optional

import httpx

from extralit.v2._api._errors import AuthError, error_from_response

_API_PREFIX = "/api/v2"


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


class AsyncTransport:
    """One httpx.AsyncClient per client instance. Auth modes: api_key header (default,
    no token lifecycle) or username/password -> bearer JWT with a single transparent
    refresh on 401 (then AuthError)."""

    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 5,
        extra_headers: Optional[dict] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._username = username
        self._password = password
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._http = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=timeout,
            transport=httpx.AsyncHTTPTransport(retries=retries),
            headers=extra_headers or {},
        )

    def _auth_headers(self) -> dict:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        if self._api_key:
            return {"X-Extralit-Api-Key": self._api_key}
        return {}

    async def _login(self) -> None:
        response = await self._http.post(
            f"{_API_PREFIX}/token", data={"username": self._username, "password": self._password}
        )
        if response.status_code >= 400:
            raise AuthError(response.status_code, _safe_json(response))
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token")

    async def _refresh(self) -> bool:
        if not self._refresh_token:
            return False
        response = await self._http.post(
            f"{_API_PREFIX}/token/refresh", json={"refresh_token": self._refresh_token}
        )
        if response.status_code >= 400:
            return False
        payload = response.json()
        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token", self._refresh_token)
        return True

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
    ) -> Any:
        if self._username and not self._access_token and not self._api_key:
            await self._login()
        response = await self._http.request(
            method, f"{_API_PREFIX}{path}", params=params, json=json, headers=self._auth_headers()
        )
        if response.status_code == 401 and self._access_token and await self._refresh():
            response = await self._http.request(
                method, f"{_API_PREFIX}{path}", params=params, json=json, headers=self._auth_headers()
            )
        if response.status_code >= 400:
            raise error_from_response(response.status_code, _safe_json(response))
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def aclose(self) -> None:
        await self._http.aclose()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_transport.py -v --disable-warnings`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/_api/_transport.py tests/unit/v2/test_transport.py
git commit -m "feat(sdk-v2): async transport with api-key/bearer auth and refresh-once"
```

---

### Task 4: Domain models and response-value wrap/unwrap

**Files:**
- Create: `src/extralit/v2/models.py`, `tests/unit/v2/test_models.py`

**Interfaces:**
- Consumes: generated DTOs from Task 1.
- Produces (all constructed via `Model.model_validate(payload)`):
  - `class Schema(SchemaRead)`, `class Record(RecordRead)`, `class Question(QuestionRead)`, `class Suggestion(SuggestionRead)` — plain subclasses
  - `class SchemaVersion(SchemaVersionRead)` with `def find_column(self, name: str) -> Optional[dict]`
  - `class Response(ResponseRead)` with property `unwrapped_values: dict`
  - `class SearchPage(BaseModel)` — `items: list[Record]`, `total: int` (approximate)
  - `def wrap_response_values(values: dict) -> dict`, `def unwrap_response_values(values) -> dict`
  - Re-exports: `ProjectionCell`, `ProjectionRecord`, `ProjectionView`, `ReferenceGroup`, `ReferenceView`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_models.py`:

```python
import uuid
from datetime import datetime, timezone

from extralit.v2.models import (
    Record,
    Response,
    SchemaVersion,
    SearchPage,
    unwrap_response_values,
    wrap_response_values,
)


def _version_payload(**overrides):
    payload = {
        "id": str(uuid.uuid4()),
        "schema_id": str(uuid.uuid4()),
        "version": 1,
        "object_key": "schemas/x/v1.json",
        "object_version_id": None,
        "etag": "e",
        "checksum": "c",
        "parent_version_id": None,
        "columns_cache": [{"name": "size", "dtype": "str"}, {"name": "country", "dtype": "str"}],
        "review_widgets": {},
        "inserted_at": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_schema_version_find_column():
    version = SchemaVersion.model_validate(_version_payload())
    assert version.find_column("size") == {"name": "size", "dtype": "str"}
    assert version.find_column("nope") is None


def test_wrap_unwrap_roundtrip():
    """Server double-wraps response values ({name: {"value": ...}}) on both PUT and GET."""
    values = {"size": "120", "country": ["KE", "UG"]}
    wrapped = wrap_response_values(values)
    assert wrapped == {"size": {"value": "120"}, "country": {"value": ["KE", "UG"]}}
    assert unwrap_response_values(wrapped) == values
    assert unwrap_response_values(None) == {}


def test_response_unwrapped_values():
    response = Response.model_validate(
        {
            "id": str(uuid.uuid4()),
            "record_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "values": {"size": {"value": "135"}},
            "status": "submitted",
            "inserted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    assert response.unwrapped_values == {"size": "135"}


def test_search_page_holds_records():
    record = {
        "id": str(uuid.uuid4()),
        "schema_id": str(uuid.uuid4()),
        "schema_version_id": str(uuid.uuid4()),
        "reference": "10.1000/xyz",
        "external_id": None,
        "fields": {"size": "120"},
        "metadata": None,
        "status": "pending",
        "inserted_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    page = SearchPage(items=[Record.model_validate(record)], total=1)
    assert page.items[0].reference == "10.1000/xyz"
    assert page.total == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_models.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2.models'`

- [ ] **Step 3: Implement**

`src/extralit/v2/models.py` (no `from __future__ import annotations` here — pydantic models on 3.9, so use `Optional`/builtin generics directly):

```python
from typing import Any, Optional

from pydantic import BaseModel

from extralit.v2._api._generated import (
    ProjectionCell,
    ProjectionRecord,
    ProjectionView,
    QuestionRead,
    RecordRead,
    ReferenceGroup,
    ReferenceView,
    ResponseRead,
    SchemaRead,
    SchemaVersionRead,
    SuggestionRead,
)

__all__ = [
    "Schema", "SchemaVersion", "Record", "Question", "Suggestion", "Response", "SearchPage",
    "ProjectionCell", "ProjectionRecord", "ProjectionView", "ReferenceGroup", "ReferenceView",
    "wrap_response_values", "unwrap_response_values",
]


class Schema(SchemaRead):
    pass


class SchemaVersion(SchemaVersionRead):
    def find_column(self, name: str) -> Optional[dict]:
        for column in self.columns_cache:
            if column.get("name") == name:
                return column
        return None


class Record(RecordRead):
    pass


class Question(QuestionRead):
    pass


class Suggestion(SuggestionRead):
    pass


def wrap_response_values(values: dict) -> dict:
    """Server stores response values double-wrapped: {question_name: {"value": ...}}."""
    return {name: {"value": value} for name, value in values.items()}


def unwrap_response_values(values: Optional[dict]) -> dict:
    return {
        name: cell.get("value") if isinstance(cell, dict) else cell
        for name, cell in (values or {}).items()
    }


class Response(ResponseRead):
    @property
    def unwrapped_values(self) -> dict:
        return unwrap_response_values(self.values)


class SearchPage(BaseModel):
    """One page of records. `total` is approximate: stale index ids are skipped and
    FTS saturates (~10k) — never present it as an exact count."""

    items: "list[Record]"
    total: int
```

Note: if `_generated.py` field types make subclass validation fail (e.g. enum vs str), check the generated field names — the contract test in Task 1 pinned the class names, and these tests pin the field behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_models.py -v --disable-warnings`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/models.py tests/unit/v2/test_models.py
git commit -m "feat(sdk-v2): domain models with double-wrap value helpers"
```

---

### Task 5: Schemas resource (create/list/get/get_by_name/update/publish/versions/columns)

**Files:**
- Create: `src/extralit/v2/resources/__init__.py`, `src/extralit/v2/resources/_base.py`, `src/extralit/v2/resources/_schemas.py`, `tests/unit/v2/test_schemas_resource.py`

**Interfaces:**
- Consumes: `AsyncTransport.request` (Task 3), models (Task 4), `NotFoundError` (Task 2).
- Produces:
  - `class ResourceBase` — `def __init__(self, transport: AsyncTransport)`, attr `self._transport`
  - `class Schemas(ResourceBase)` with async methods:
    - `create(workspace_id, name, settings=None) -> Schema`
    - `list(workspace_id) -> list[Schema]`
    - `get(schema_id) -> Schema`
    - `get_by_name(workspace_id, name) -> Schema` (raises `NotFoundError(404, ...)` when absent)
    - `update(schema_id, *, name=None, settings=None) -> Schema`
    - `publish(schema_id, schema, review_widgets=None) -> SchemaVersion` — `schema` is a Pandera `DataFrameSchema` (duck-typed via `.to_json()`) or an already-serialized JSON string
    - `versions(schema_id) -> list[SchemaVersion]`
    - `get_version(schema_id, version: int) -> SchemaVersion` — cached by `(schema_id, version)` (immutable)
    - `columns(schema_id) -> list[dict]`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_schemas_resource.py`:

```python
import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Schemas

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
WS = str(uuid.uuid4())
SCHEMA_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _schema(name="trials"):
    return {
        "id": SCHEMA_ID, "name": name, "status": "draft", "current_version_id": None,
        "settings": {}, "workspace_id": WS, "inserted_at": NOW, "updated_at": NOW,
    }


def _version(version=1):
    return {
        "id": str(uuid.uuid4()), "schema_id": SCHEMA_ID, "version": version,
        "object_key": f"schemas/{SCHEMA_ID}/v{version}.json", "object_version_id": None,
        "etag": "e", "checksum": "c", "parent_version_id": None,
        "columns_cache": [{"name": "size"}], "review_widgets": {}, "inserted_at": NOW,
    }


@pytest.fixture
async def schemas():
    transport = AsyncTransport(API, api_key="k")
    yield Schemas(transport)
    await transport.aclose()


async def test_create_and_get(httpx_mock, schemas):
    httpx_mock.add_response(method="POST", url=f"{API}/api/v2/schemas", status_code=201, json=_schema())
    created = await schemas.create(WS, "trials")
    assert created.name == "trials"
    body = httpx_mock.get_requests()[0].read()
    assert b'"workspace_id"' in body and b'"trials"' in body


async def test_get_by_name_found_and_missing(httpx_mock, schemas):
    listing = {"items": [_schema("other") | {"id": str(uuid.uuid4())}, _schema("trials")]}
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id={WS}", json=listing)
    found = await schemas.get_by_name(WS, "trials")
    assert str(found.id) == SCHEMA_ID
    httpx_mock.add_response(url=f"{API}/api/v2/schemas?workspace_id={WS}", json={"items": []})
    with pytest.raises(NotFoundError):
        await schemas.get_by_name(WS, "trials")


async def test_publish_accepts_pandera_object_or_string(httpx_mock, schemas):
    httpx_mock.add_response(
        method="POST", url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions", status_code=201, json=_version()
    )

    class FakePandera:  # duck-type: anything with .to_json()
        def to_json(self):
            return '{"columns": {"size": {}}}'

    version = await schemas.publish(SCHEMA_ID, FakePandera(), review_widgets={"size": {"widget": "text"}})
    assert version.version == 1
    sent = httpx_mock.get_requests()[0].read()
    assert b'"columns"' in sent and b'"review_widgets"' in sent


async def test_get_version_cached(httpx_mock, schemas):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions/1", json=_version())
    v1 = await schemas.get_version(SCHEMA_ID, 1)
    v1_again = await schemas.get_version(SCHEMA_ID, 1)  # served from cache: no second request
    assert v1_again is v1
    assert len(httpx_mock.get_requests()) == 1


async def test_versions_and_columns(httpx_mock, schemas):
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/versions", json=[_version(1), _version(2)])
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/columns", json=[{"name": "size"}])
    assert [v.version for v in await schemas.versions(SCHEMA_ID)] == [1, 2]
    assert await schemas.columns(SCHEMA_ID) == [{"name": "size"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_schemas_resource.py -v --disable-warnings`
Expected: FAIL — `ImportError` (no `extralit.v2.resources`)

- [ ] **Step 3: Implement**

`src/extralit/v2/resources/_base.py`:

```python
from extralit.v2._api._transport import AsyncTransport


class ResourceBase:
    def __init__(self, transport: AsyncTransport):
        self._transport = transport
```

`src/extralit/v2/resources/_schemas.py`:

```python
from __future__ import annotations

from typing import Any, Optional

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Schema, SchemaVersion
from extralit.v2.resources._base import ResourceBase


class Schemas(ResourceBase):
    def __init__(self, transport: AsyncTransport):
        super().__init__(transport)
        self._version_cache: dict = {}  # (schema_id, version) -> SchemaVersion; versions are immutable

    async def create(self, workspace_id, name: str, settings: Optional[dict] = None) -> Schema:
        payload = await self._transport.request(
            "POST", "/schemas",
            json={"name": name, "workspace_id": str(workspace_id), "settings": settings or {}},
        )
        return Schema.model_validate(payload)

    async def list(self, workspace_id) -> list[Schema]:
        payload = await self._transport.request("GET", "/schemas", params={"workspace_id": str(workspace_id)})
        return [Schema.model_validate(item) for item in payload["items"]]

    async def get(self, schema_id) -> Schema:
        return Schema.model_validate(await self._transport.request("GET", f"/schemas/{schema_id}"))

    async def get_by_name(self, workspace_id, name: str) -> Schema:
        for schema in await self.list(workspace_id):
            if schema.name == name:
                return schema
        raise NotFoundError(404, f"schema named {name!r} not found in workspace {workspace_id}")

    async def update(self, schema_id, *, name: Optional[str] = None, settings: Optional[dict] = None) -> Schema:
        body: dict = {}
        if name is not None:
            body["name"] = name
        if settings is not None:
            body["settings"] = settings
        return Schema.model_validate(await self._transport.request("PUT", f"/schemas/{schema_id}", json=body))

    async def publish(self, schema_id, schema: Any, review_widgets: Optional[dict] = None) -> SchemaVersion:
        """Publish a new schema version. `schema` is a pandera DataFrameSchema (anything with
        .to_json()) or the already-serialized JSON string. review_widgets ride out-of-band
        because pandera's to_json() drops Column.metadata."""
        body = schema.to_json() if hasattr(schema, "to_json") else schema
        payload = await self._transport.request(
            "POST", f"/schemas/{schema_id}/versions",
            json={"body": body, "review_widgets": review_widgets or {}},
        )
        version = SchemaVersion.model_validate(payload)
        self._version_cache[(str(schema_id), version.version)] = version
        return version

    async def versions(self, schema_id) -> list[SchemaVersion]:
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/versions")
        return [SchemaVersion.model_validate(item) for item in payload]

    async def get_version(self, schema_id, version: int) -> SchemaVersion:
        key = (str(schema_id), version)
        if key not in self._version_cache:
            payload = await self._transport.request("GET", f"/schemas/{schema_id}/versions/{version}")
            self._version_cache[key] = SchemaVersion.model_validate(payload)
        return self._version_cache[key]

    async def columns(self, schema_id) -> list[dict]:
        return await self._transport.request("GET", f"/schemas/{schema_id}/columns")
```

`src/extralit/v2/resources/__init__.py`:

```python
from extralit.v2.resources._schemas import Schemas

__all__ = ["Schemas"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_schemas_resource.py -v --disable-warnings`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/resources tests/unit/v2/test_schemas_resource.py
git commit -m "feat(sdk-v2): Schemas resource with immutable version caching"
```

---

### Task 6: Questions resource with cached name→id map

**Files:**
- Create: `src/extralit/v2/resources/_questions.py`, `tests/unit/v2/test_questions_resource.py`
- Modify: `src/extralit/v2/resources/__init__.py`

**Interfaces:**
- Consumes: `ResourceBase`, `Question` model, `NotFoundError`.
- Produces: `class Questions(ResourceBase)`:
  - `async def list(self, schema_id) -> list[Question]`
  - `async def get(self, question_id) -> Question`
  - `async def id_for(self, schema_id, name: str) -> UUID` — cached per schema; on a cache miss for a known schema it refetches once (a question may have been added) before raising `NotFoundError`. **This is the name↔id join used by Suggestions — suggestions key by question id, while cells/response values key by name.**
  - `def invalidate(self, schema_id) -> None` — drops the cached map

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_questions_resource.py`:

```python
import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Questions

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
Q_SIZE = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _question(qid, name):
    return {
        "id": qid, "schema_id": SCHEMA_ID, "name": name, "title": name.title(), "description": None,
        "type": "text", "columns": [name], "settings": {}, "required": False,
        "inserted_at": NOW, "updated_at": NOW,
    }


@pytest.fixture
async def questions():
    transport = AsyncTransport(API, api_key="k")
    yield Questions(transport)
    await transport.aclose()


async def test_list_and_id_for_uses_one_fetch(httpx_mock, questions):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions", json={"items": [_question(Q_SIZE, "size")]}
    )
    assert [q.name for q in await questions.list(SCHEMA_ID)] == ["size"]
    assert str(await questions.id_for(SCHEMA_ID, "size")) == Q_SIZE  # served from cache
    assert len(httpx_mock.get_requests()) == 1


async def test_id_for_refetches_once_then_raises(httpx_mock, questions):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions", json={"items": [_question(Q_SIZE, "size")]}
    )
    await questions.list(SCHEMA_ID)
    q_new = str(uuid.uuid4())
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={"items": [_question(Q_SIZE, "size"), _question(q_new, "dosage")]},
    )
    assert str(await questions.id_for(SCHEMA_ID, "dosage")) == q_new  # miss -> refetch -> hit
    httpx_mock.add_response(url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions", json={"items": []})
    with pytest.raises(NotFoundError):
        await questions.id_for(SCHEMA_ID, "ghost")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_questions_resource.py -v --disable-warnings`
Expected: FAIL — `ImportError: cannot import name 'Questions'`

- [ ] **Step 3: Implement**

`src/extralit/v2/resources/_questions.py`:

```python
from __future__ import annotations

from uuid import UUID

from extralit.v2._api._errors import NotFoundError
from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Question
from extralit.v2.resources._base import ResourceBase


class Questions(ResourceBase):
    """Callers address questions by NAME; the server keys suggestions by question ID
    (cells/response values key by name). This resource owns that join via a cached map."""

    def __init__(self, transport: AsyncTransport):
        super().__init__(transport)
        self._maps: dict = {}  # str(schema_id) -> {name: UUID}

    async def list(self, schema_id) -> list[Question]:
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/questions")
        items = [Question.model_validate(item) for item in payload["items"]]
        self._maps[str(schema_id)] = {q.name: q.id for q in items}
        return items

    async def get(self, question_id) -> Question:
        return Question.model_validate(await self._transport.request("GET", f"/questions/{question_id}"))

    async def id_for(self, schema_id, name: str) -> UUID:
        key = str(schema_id)
        if key not in self._maps or name not in self._maps[key]:
            await self.list(schema_id)  # refetch once: the question may be newly created
        if name not in self._maps.get(key, {}):
            raise NotFoundError(404, f"question named {name!r} not found in schema {schema_id}")
        return self._maps[key][name]

    def invalidate(self, schema_id) -> None:
        self._maps.pop(str(schema_id), None)
```

Update `src/extralit/v2/resources/__init__.py`:

```python
from extralit.v2.resources._questions import Questions
from extralit.v2.resources._schemas import Schemas

__all__ = ["Questions", "Schemas"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_questions_resource.py -v --disable-warnings`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/resources tests/unit/v2/test_questions_resource.py
git commit -m "feat(sdk-v2): Questions resource owning the name-to-id join"
```

---

### Task 7: Records resource — chunked concurrent bulk upsert, search, list, delete

**Files:**
- Create: `src/extralit/v2/resources/_records.py`, `tests/unit/v2/test_records_resource.py`
- Modify: `src/extralit/v2/resources/__init__.py`

**Interfaces:**
- Consumes: `ResourceBase`, `Record`/`SearchPage`/`ReferenceView` models.
- Produces: `class Records(ResourceBase)`:
  - `async def bulk_upsert(self, schema_id, items, *, reference=None, max_concurrency=4, on_progress=None) -> list[Record]` — `items`: list of dicts (full `RecordUpsert` shape if a `"fields"` key is present, else treated as bare field dicts) or a pandas DataFrame (lazy import; rows become field dicts, a `reference` column is lifted out). Chunks at 500, dispatches chunks concurrently under a semaphore, preserves input order in the returned list. `on_progress(done_count, total_count)` called per completed chunk.
  - `async def search(self, schema_id, *, text=None, filters=None, offset=0, limit=50) -> SearchPage` — `filters`: list of `(column, op, value)` tuples or `{"column","op","value"}` dicts, `op ∈ {eq,in,ge,le}`.
  - `async def list(self, schema_id, *, offset=0, limit=50, status=None, reference=None) -> SearchPage`
  - `async def delete(self, schema_id, ids) -> None` — chunks at 100 ids per request (comma-separated query param).
  - `async def get_reference(self, workspace_id, reference: str) -> ReferenceView` — path is NOT url-encoded for slashes (server route is `{reference:path}`).

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_records_resource.py`:

```python
import json
import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Records

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _record(i):
    return {
        "id": str(uuid.uuid4()), "schema_id": SCHEMA_ID, "schema_version_id": str(uuid.uuid4()),
        "reference": "10.1000/xyz", "external_id": str(i), "fields": {"size": str(i)},
        "metadata": None, "status": "pending", "inserted_at": NOW, "updated_at": NOW,
    }


@pytest.fixture
async def records():
    transport = AsyncTransport(API, api_key="k")
    yield Records(transport)
    await transport.aclose()


async def test_bulk_upsert_chunks_at_500_and_preserves_order(httpx_mock, records):
    url = f"{API}/api/v2/schemas/{SCHEMA_ID}/records:bulk-upsert"

    def responder(request):
        import httpx

        sent = json.loads(request.read())["items"]
        assert len(sent) <= 500
        return httpx.Response(200, json={"items": [_record(item["external_id"]) for item in sent], "total": len(sent)})

    for _ in range(3):
        httpx_mock.add_callback(responder, method="POST", url=url)

    items = [{"fields": {"size": str(i)}, "reference": "10.1000/xyz", "external_id": str(i)} for i in range(1200)]
    progress = []
    result = await records.bulk_upsert(SCHEMA_ID, items, on_progress=lambda done, total: progress.append((done, total)))
    assert len(result) == 1200
    assert [r.external_id for r in result] == [str(i) for i in range(1200)]  # input order preserved
    assert len(httpx_mock.get_requests()) == 3  # 500 + 500 + 200
    assert progress[-1] == (1200, 1200)


async def test_bulk_upsert_bare_fields_and_shared_reference(httpx_mock, records):
    url = f"{API}/api/v2/schemas/{SCHEMA_ID}/records:bulk-upsert"
    httpx_mock.add_response(method="POST", url=url, json={"items": [_record(0)], "total": 1})
    await records.bulk_upsert(SCHEMA_ID, [{"size": "120"}], reference="10.1000/xyz")
    sent = json.loads(httpx_mock.get_requests()[0].read())["items"]
    assert sent == [{"fields": {"size": "120"}, "reference": "10.1000/xyz"}]


async def test_bulk_upsert_without_reference_raises(records):
    with pytest.raises(ValueError, match="reference"):
        await records.bulk_upsert(SCHEMA_ID, [{"size": "120"}])


async def test_bulk_upsert_accepts_dataframe(httpx_mock, records):
    pandas = pytest.importorskip("pandas")
    url = f"{API}/api/v2/schemas/{SCHEMA_ID}/records:bulk-upsert"
    httpx_mock.add_response(method="POST", url=url, json={"items": [_record(0), _record(1)], "total": 2})
    frame = pandas.DataFrame([
        {"size": "120", "reference": "10.1000/a"},
        {"size": "135", "reference": "10.1000/b"},
    ])
    await records.bulk_upsert(SCHEMA_ID, frame)
    sent = json.loads(httpx_mock.get_requests()[0].read())["items"]
    assert sent == [
        {"fields": {"size": "120"}, "reference": "10.1000/a"},
        {"fields": {"size": "135"}, "reference": "10.1000/b"},
    ]


async def test_search_normalizes_tuple_filters(httpx_mock, records):
    url = f"{API}/api/v2/schemas/{SCHEMA_ID}/records:search"
    httpx_mock.add_response(method="POST", url=url, json={"items": [_record(1)], "total": 41})
    page = await records.search(SCHEMA_ID, text="tumor", filters=[("age", "ge", 18)], limit=10)
    assert page.total == 41
    body = json.loads(httpx_mock.get_requests()[0].read())
    assert body == {
        "text": "tumor",
        "filters": [{"column": "age", "op": "ge", "value": 18}],
        "offset": 0,
        "limit": 10,
    }


async def test_list_passes_status_and_reference(httpx_mock, records):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/records?offset=0&limit=50&status=pending&reference=10.1000%2Fxyz",
        json={"items": [], "total": 0},
    )
    page = await records.list(SCHEMA_ID, status="pending", reference="10.1000/xyz")
    assert page.items == [] and page.total == 0


async def test_delete_chunks_at_100(httpx_mock, records):
    for _ in range(2):
        httpx_mock.add_response(
            method="DELETE",
            url=__import__("re").compile(rf"{API}/api/v2/schemas/{SCHEMA_ID}/records\?ids=.*"),
            status_code=204,
        )
    await records.delete(SCHEMA_ID, [f"id-{i}" for i in range(150)])
    reqs = httpx_mock.get_requests()
    assert len(reqs) == 2
    assert len(reqs[0].url.params["ids"].split(",")) == 100
    assert len(reqs[1].url.params["ids"].split(",")) == 50


async def test_get_reference_keeps_slashes(httpx_mock, records):
    httpx_mock.add_response(
        url=f"{API}/api/v2/references/10.1000/j.abc?workspace_id={WS}",
        json={"reference": "10.1000/j.abc", "groups": [], "total_records": 0},
    )
    view = await records.get_reference(WS, "10.1000/j.abc")
    assert view.reference == "10.1000/j.abc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_records_resource.py -v --disable-warnings`
Expected: FAIL — `ImportError: cannot import name 'Records'`

- [ ] **Step 3: Implement**

`src/extralit/v2/resources/_records.py`:

```python
from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from extralit.v2.models import Record, ReferenceView, SearchPage
from extralit.v2.resources._base import ResourceBase

BULK_UPSERT_MAX_ITEMS = 500  # server cap (RECORDS_BULK_UPSERT_MAX_ITEMS)
DELETE_MAX_IDS = 100  # server cap (DELETE_RECORDS_LIMIT)


def _normalize_items(items: Any, reference: Optional[str]) -> list[dict]:
    if hasattr(items, "to_dict") and hasattr(items, "columns"):  # pandas.DataFrame, kept lazy
        items = items.to_dict(orient="records")
    normalized = []
    for item in items:
        if "fields" in item:
            entry = dict(item)
        else:
            fields = dict(item)
            entry = {"fields": fields}
            if "reference" in fields:
                entry["reference"] = fields.pop("reference")
        if reference is not None:
            entry.setdefault("reference", reference)
        if "reference" not in entry:
            raise ValueError("every record needs a reference (per-item or via the reference= argument)")
        normalized.append(entry)
    return normalized


def _normalize_filters(filters: Optional[list]) -> list[dict]:
    normalized = []
    for item in filters or []:
        if isinstance(item, dict):
            normalized.append({"column": item["column"], "op": item["op"], "value": item["value"]})
        else:
            column, op, value = item
            normalized.append({"column": column, "op": op, "value": value})
    return normalized


class Records(ResourceBase):
    async def bulk_upsert(
        self,
        schema_id,
        items: Any,
        *,
        reference: Optional[str] = None,
        max_concurrency: int = 4,
        on_progress: Optional[Callable] = None,
    ) -> list[Record]:
        """Idempotent on external_id; metadata is patch-like (omitted keys preserved).
        Auto-chunks at the server's 500-item cap; chunks fly concurrently but the
        returned list preserves input order."""
        normalized = _normalize_items(items, reference)
        chunks = [normalized[i : i + BULK_UPSERT_MAX_ITEMS] for i in range(0, len(normalized), BULK_UPSERT_MAX_ITEMS)]
        results: list = [None] * len(chunks)
        total = len(normalized)
        done = 0
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run(index: int, chunk: list[dict]) -> None:
            nonlocal done
            async with semaphore:
                payload = await self._transport.request(
                    "POST", f"/schemas/{schema_id}/records:bulk-upsert", json={"items": chunk}
                )
            results[index] = payload["items"]
            done += len(chunk)
            if on_progress:
                on_progress(done, total)

        await asyncio.gather(*(_run(i, c) for i, c in enumerate(chunks)))
        return [Record.model_validate(item) for chunk in results for item in chunk]

    async def search(
        self,
        schema_id,
        *,
        text: Optional[str] = None,
        filters: Optional[list] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> SearchPage:
        payload = await self._transport.request(
            "POST",
            f"/schemas/{schema_id}/records:search",
            json={"text": text, "filters": _normalize_filters(filters), "offset": offset, "limit": limit},
        )
        return SearchPage(items=[Record.model_validate(i) for i in payload["items"]], total=payload["total"])

    async def list(
        self,
        schema_id,
        *,
        offset: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        reference: Optional[str] = None,
    ) -> SearchPage:
        params: dict = {"offset": offset, "limit": limit}
        if status is not None:
            params["status"] = status
        if reference is not None:
            params["reference"] = reference
        payload = await self._transport.request("GET", f"/schemas/{schema_id}/records", params=params)
        return SearchPage(items=[Record.model_validate(i) for i in payload["items"]], total=payload["total"])

    async def delete(self, schema_id, ids: list) -> None:
        id_strings = [str(record_id) for record_id in ids]
        for start in range(0, len(id_strings), DELETE_MAX_IDS):
            chunk = id_strings[start : start + DELETE_MAX_IDS]
            await self._transport.request(
                "DELETE", f"/schemas/{schema_id}/records", params={"ids": ",".join(chunk)}
            )

    async def get_reference(self, workspace_id, reference: str) -> ReferenceView:
        # Slashes stay raw: the server route is /references/{reference:path}.
        payload = await self._transport.request(
            "GET", f"/references/{reference}", params={"workspace_id": str(workspace_id)}
        )
        return ReferenceView.model_validate(payload)
```

Update `src/extralit/v2/resources/__init__.py`:

```python
from extralit.v2.resources._questions import Questions
from extralit.v2.resources._records import Records
from extralit.v2.resources._schemas import Schemas

__all__ = ["Questions", "Records", "Schemas"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_records_resource.py -v --disable-warnings`
Expected: 8 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/resources tests/unit/v2/test_records_resource.py
git commit -m "feat(sdk-v2): Records resource with chunked concurrent bulk upsert and search"
```

---

### Task 8: Suggestions, Projections, and Responses (read-only) resources

**Files:**
- Create: `src/extralit/v2/resources/_annotation.py`, `src/extralit/v2/resources/_projections.py`, `tests/unit/v2/test_annotation_resources.py`
- Modify: `src/extralit/v2/resources/__init__.py`

**Interfaces:**
- Consumes: `Questions.id_for` (Task 6), models (Task 4).
- Produces:
  - `class Suggestions(ResourceBase)` — `def __init__(self, transport, questions: Questions)`;
    - `async def upsert(self, record, question, value, *, score=None, agent=None, type=None, schema_id=None) -> Suggestion` — `record`: a `Record` domain object or a record id; `question`: a question id (UUID/uuid-string) or a question **name**. A name needs a schema to resolve against: taken from `record.schema_id` when a `Record` object was passed, else from `schema_id=`; otherwise `ValueError`.
    - `async def list(self, record_id) -> list[Suggestion]`
  - `class Responses(ResourceBase)` — `async def get(self, record_id) -> Optional[Response]` — the server returns literal `null` with 200 when no response exists: map to `None`, not an error.
  - `class Projections(ResourceBase)` — `async def get(self, workspace_id, reference: str) -> ProjectionView`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_annotation_resources.py`:

```python
import json
import uuid
from datetime import datetime, timezone

import pytest

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Record
from extralit.v2.resources import Projections, Questions, Responses, Suggestions

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
RECORD_ID = str(uuid.uuid4())
Q_SIZE = str(uuid.uuid4())
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _suggestion():
    return {
        "id": str(uuid.uuid4()), "record_id": RECORD_ID, "question_id": Q_SIZE, "value": "120",
        "score": 0.9, "agent": "claude", "type": "model", "inserted_at": NOW, "updated_at": NOW,
    }


def _record_obj():
    return Record.model_validate(
        {
            "id": RECORD_ID, "schema_id": SCHEMA_ID, "schema_version_id": str(uuid.uuid4()),
            "reference": "10.1000/xyz", "external_id": None, "fields": {}, "metadata": None,
            "status": "pending", "inserted_at": NOW, "updated_at": NOW,
        }
    )


@pytest.fixture
async def transport():
    t = AsyncTransport(API, api_key="k")
    yield t
    await t.aclose()


async def test_upsert_resolves_question_name_via_record_object(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/schemas/{SCHEMA_ID}/questions",
        json={"items": [{
            "id": Q_SIZE, "schema_id": SCHEMA_ID, "name": "size", "title": "Size", "description": None,
            "type": "text", "columns": ["size"], "settings": {}, "required": False,
            "inserted_at": NOW, "updated_at": NOW,
        }]},
    )
    httpx_mock.add_response(
        method="PUT", url=f"{API}/api/v2/records/{RECORD_ID}/suggestions", json=_suggestion()
    )
    questions = Questions(transport)
    suggestions = Suggestions(transport, questions)
    result = await suggestions.upsert(_record_obj(), "size", "120", score=0.9, agent="claude")
    assert str(result.question_id) == Q_SIZE
    body = json.loads(httpx_mock.get_requests()[-1].read())
    assert body["question_id"] == Q_SIZE and body["agent"] == "claude" and body["score"] == 0.9


async def test_upsert_name_without_schema_raises(transport):
    suggestions = Suggestions(transport, Questions(transport))
    with pytest.raises(ValueError, match="schema_id"):
        await suggestions.upsert(RECORD_ID, "size", "120")


async def test_upsert_accepts_question_id_directly(httpx_mock, transport):
    httpx_mock.add_response(
        method="PUT", url=f"{API}/api/v2/records/{RECORD_ID}/suggestions", json=_suggestion()
    )
    suggestions = Suggestions(transport, Questions(transport))
    await suggestions.upsert(RECORD_ID, Q_SIZE, "120")  # no questions fetch needed
    assert len(httpx_mock.get_requests()) == 1


async def test_response_get_maps_null_to_none(httpx_mock, transport):
    httpx_mock.add_response(url=f"{API}/api/v2/records/{RECORD_ID}/responses", json=None)
    assert await Responses(transport).get(RECORD_ID) is None


async def test_response_get_unwraps_values(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/records/{RECORD_ID}/responses",
        json={
            "id": str(uuid.uuid4()), "record_id": RECORD_ID, "user_id": str(uuid.uuid4()),
            "values": {"size": {"value": "135"}}, "status": "submitted",
            "inserted_at": NOW, "updated_at": NOW,
        },
    )
    response = await Responses(transport).get(RECORD_ID)
    assert response.unwrapped_values == {"size": "135"}


async def test_projection_get(httpx_mock, transport):
    httpx_mock.add_response(
        url=f"{API}/api/v2/projection/references/10.1000/j.abc?workspace_id={WS}",
        json={
            "reference": "10.1000/j.abc",
            "records": [{
                "record_id": RECORD_ID, "schema_id": SCHEMA_ID, "reference": "10.1000/j.abc",
                "cells": [{"question_name": "size", "value": "120", "source": "suggestion"}],
            }],
            "total_records": 1,
        },
    )
    view = await Projections(transport).get(WS, "10.1000/j.abc")
    assert view.records[0].cells[0].source == "suggestion"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_annotation_resources.py -v --disable-warnings`
Expected: FAIL — `ImportError` on `Projections`/`Responses`/`Suggestions`

- [ ] **Step 3: Implement**

`src/extralit/v2/resources/_annotation.py`:

```python
from __future__ import annotations

import uuid
from typing import Any, Optional

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.models import Response, Suggestion
from extralit.v2.resources._base import ResourceBase
from extralit.v2.resources._questions import Questions


def _as_question_id(question: Any) -> Optional[str]:
    try:
        return str(uuid.UUID(str(question)))
    except (ValueError, AttributeError, TypeError):
        return None


class Suggestions(ResourceBase):
    def __init__(self, transport: AsyncTransport, questions: Questions):
        super().__init__(transport)
        self._questions = questions

    async def upsert(
        self,
        record: Any,
        question: Any,
        value: Any,
        *,
        score: Optional[Any] = None,
        agent: Optional[str] = None,
        type: Optional[str] = None,
        schema_id: Optional[Any] = None,
    ) -> Suggestion:
        """Upsert one suggestion per (record, question). Suggestions key by question ID on
        the wire, but callers may pass a question NAME — resolved via the record's schema."""
        record_id = getattr(record, "id", record)
        question_id = _as_question_id(question)
        if question_id is None:  # a name: resolve against the record's schema
            resolve_schema = getattr(record, "schema_id", None) or schema_id
            if resolve_schema is None:
                raise ValueError(
                    "resolving a question name requires a Record object or an explicit schema_id="
                )
            question_id = str(await self._questions.id_for(resolve_schema, question))
        body: dict = {"question_id": question_id, "value": value}
        if score is not None:
            body["score"] = score
        if agent is not None:
            body["agent"] = agent
        if type is not None:
            body["type"] = type
        payload = await self._transport.request("PUT", f"/records/{record_id}/suggestions", json=body)
        return Suggestion.model_validate(payload)

    async def list(self, record_id) -> list[Suggestion]:
        payload = await self._transport.request("GET", f"/records/{record_id}/suggestions")
        return [Suggestion.model_validate(item) for item in payload["items"]]


class Responses(ResourceBase):
    async def get(self, record_id) -> Optional[Response]:
        """GET returns literal `null` with 200 (not 404) when no response exists yet."""
        payload = await self._transport.request("GET", f"/records/{record_id}/responses")
        return None if payload is None else Response.model_validate(payload)
```

`src/extralit/v2/resources/_projections.py`:

```python
from extralit.v2.models import ProjectionView
from extralit.v2.resources._base import ResourceBase


class Projections(ResourceBase):
    async def get(self, workspace_id, reference: str) -> ProjectionView:
        """Response-or-suggestion per question for every record sharing this reference.
        Slashes stay raw: the server route is /projection/references/{reference:path}."""
        payload = await self._transport.request(
            "GET", f"/projection/references/{reference}", params={"workspace_id": str(workspace_id)}
        )
        return ProjectionView.model_validate(payload)
```

Update `src/extralit/v2/resources/__init__.py`:

```python
from extralit.v2.resources._annotation import Responses, Suggestions
from extralit.v2.resources._projections import Projections
from extralit.v2.resources._questions import Questions
from extralit.v2.resources._records import Records
from extralit.v2.resources._schemas import Schemas

__all__ = ["Projections", "Questions", "Records", "Responses", "Schemas", "Suggestions"]
```

Note: `json=None` in the `test_response_get_maps_null_to_none` mock makes httpx return a body of `null` — the transport returns `None` because `response.json()` is `None`? No: the transport checks `not response.content` — a `null` body has content `b"null"`, so `response.json()` returns `None` naturally. Either path yields `None`; the test pins the behavior.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_annotation_resources.py -v --disable-warnings`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/resources tests/unit/v2/test_annotation_resources.py
git commit -m "feat(sdk-v2): Suggestions/Responses/Projections resources with name-id join"
```

---

### Task 9: AsyncClient assembly with env/credentials fallback

**Files:**
- Create: `src/extralit/v2/client.py`, `tests/unit/v2/test_client.py`
- Modify: `src/extralit/v2/__init__.py`

**Interfaces:**
- Consumes: everything above; `extralit.client.login.ExtralitCredentials` (the one allowed v1 import).
- Produces:
  - `class AsyncClient` — `def __init__(self, api_url=None, api_key=None, username=None, password=None, timeout=60.0, retries=5)`. Resolution order: explicit args → `EXTRALIT_API_URL`/`EXTRALIT_API_KEY` env → `~/.extralit/credentials.json`. Raises `ValueError` if unresolvable.
  - Attributes: `.schemas: Schemas`, `.questions: Questions`, `.records: Records`, `.suggestions: Suggestions`, `.projections: Projections`, `.responses: Responses` (plus `.references` → `records.get_reference` lives on Records; expose `get_reference` through `client.records`).
  - `async def aclose()`, `async def __aenter__/__aexit__`
  - `extralit.v2.__init__` exports: `AsyncClient` + all names from `models`

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_client.py -v --disable-warnings`
Expected: FAIL — `ImportError: cannot import name 'AsyncClient'`

- [ ] **Step 3: Implement**

`src/extralit/v2/client.py`:

```python
from __future__ import annotations

import os
from typing import Optional

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Projections, Questions, Records, Responses, Schemas, Suggestions


def _credentials_fallback() -> tuple:
    # The single, documented v1 import: the credentials file outlives v1 retirement.
    from extralit.client.login import ExtralitCredentials

    if not ExtralitCredentials.exists():
        return None, None
    try:
        credentials = ExtralitCredentials.load()
        return credentials.api_url, credentials.api_key
    except (OSError, KeyError, ValueError):
        return None, None


class AsyncClient:
    """Async-native /api/v2 client. Resolution order for connection settings:
    explicit args > EXTRALIT_API_URL / EXTRALIT_API_KEY env > ~/.extralit/credentials.json."""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 60.0,
        retries: int = 5,
    ):
        api_url = api_url or os.environ.get("EXTRALIT_API_URL")
        api_key = api_key or os.environ.get("EXTRALIT_API_KEY")
        if not api_url or (not api_key and not username):
            file_url, file_key = _credentials_fallback()
            api_url = api_url or file_url
            if not api_key and not username:
                api_key = file_key
        if not api_url:
            raise ValueError("api_url is required (argument, EXTRALIT_API_URL, or ~/.extralit/credentials.json)")
        if not api_key and not username:
            raise ValueError("credentials required: api_key or username/password")
        self._transport = AsyncTransport(
            api_url, api_key=api_key, username=username, password=password, timeout=timeout, retries=retries
        )
        self.schemas = Schemas(self._transport)
        self.questions = Questions(self._transport)
        self.records = Records(self._transport)
        self.suggestions = Suggestions(self._transport, self.questions)
        self.projections = Projections(self._transport)
        self.responses = Responses(self._transport)

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()
```

`src/extralit/v2/__init__.py`:

```python
from extralit.v2.client import AsyncClient
from extralit.v2.models import (
    ProjectionCell,
    ProjectionRecord,
    ProjectionView,
    Question,
    Record,
    ReferenceGroup,
    ReferenceView,
    Response,
    Schema,
    SchemaVersion,
    SearchPage,
    Suggestion,
)

__all__ = [
    "AsyncClient",
    "ProjectionCell", "ProjectionRecord", "ProjectionView", "Question", "Record",
    "ReferenceGroup", "ReferenceView", "Response", "Schema", "SchemaVersion",
    "SearchPage", "Suggestion",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_client.py -v --disable-warnings`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/client.py src/extralit/v2/__init__.py tests/unit/v2/test_client.py
git commit -m "feat(sdk-v2): AsyncClient assembly with env and credentials-file fallback"
```

---

### Task 10: Sync facade — portal + mechanical mirrors

**Files:**
- Create: `src/extralit/v2/_sync.py`, `tests/unit/v2/test_sync_client.py`
- Modify: `src/extralit/v2/__init__.py`

**Interfaces:**
- Consumes: `AsyncClient` (Task 9), resources.
- Produces:
  - `class Client` — same constructor signature as `AsyncClient`; exposes the same resource attributes where every async method is a sync mirror (dispatched to a background-thread event loop, so it works inside Jupyter where a loop is already running). `def close()`, context-manager support.
  - Export `Client` from `extralit.v2`.

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_sync_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/test_sync_client.py -v --disable-warnings`
Expected: FAIL — `ImportError: cannot import name 'Client'`

- [ ] **Step 3: Implement**

`src/extralit/v2/_sync.py`:

```python
from __future__ import annotations

import asyncio
import functools
import inspect
import threading

from extralit.v2.client import AsyncClient
from extralit.v2.resources._base import ResourceBase

_RESOURCE_NAMES = ("schemas", "questions", "records", "suggestions", "projections", "responses")


class _Portal:
    """A background-thread event loop. Sync mirrors submit coroutines here, so they
    work even when the calling thread already runs a loop (Jupyter)."""

    def __init__(self):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="extralit-v2-portal", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def run(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self._loop).result()

    def stop(self) -> None:
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()


class _SyncProxy:
    """Wraps a resource: coroutine methods become sync calls through the portal;
    everything else passes through unchanged. Mirrors are mechanical — never hand-written."""

    def __init__(self, target: ResourceBase, portal: _Portal):
        self._target = target
        self._portal = portal

    def __getattr__(self, name: str):
        attribute = getattr(self._target, name)
        if inspect.iscoroutinefunction(attribute):
            @functools.wraps(attribute)
            def call(*args, **kwargs):
                return self._portal.run(attribute(*args, **kwargs))

            return call
        return attribute


class Client:
    """Sync facade over AsyncClient — same constructor, same resource surface."""

    def __init__(self, *args, **kwargs):
        self._portal = _Portal()
        self._async = AsyncClient(*args, **kwargs)
        for name in _RESOURCE_NAMES:
            setattr(self, name, _SyncProxy(getattr(self._async, name), self._portal))

    def close(self) -> None:
        self._portal.run(self._async.aclose())
        self._portal.stop()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
```

Add to `src/extralit/v2/__init__.py` imports/`__all__`:

```python
from extralit.v2._sync import Client
```

(and `"Client"` in `__all__`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/test_sync_client.py -v --disable-warnings`
Expected: 3 PASS. Also rerun the whole v2 suite: `uv run pytest tests/unit/v2 -v --disable-warnings` — all green.

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/_sync.py src/extralit/v2/__init__.py tests/unit/v2/test_sync_client.py
git commit -m "feat(sdk-v2): sync facade via background-thread portal"
```

---

### Task 11: CLI plumbing — JSON-first output, error contract, client context

**Files:**
- Create: `src/extralit/v2/cli/__init__.py`, `src/extralit/v2/cli/_output.py`, `src/extralit/v2/cli/_context.py`, `tests/unit/v2/cli/__init__.py`, `tests/unit/v2/cli/test_output.py`

**Interfaces:**
- Consumes: `Client` (Task 10), error hierarchy (Task 2).
- Produces:
  - `_output.emit(data, json_flag: bool) -> None` — pydantic models/lists/dicts → JSON on stdout when `json_flag` **or stdout is not a TTY**; Rich table/pretty otherwise.
  - `_output.fail(error: Exception) -> NoReturn` — `{"error": {"type", "status", "detail"}}` JSON on **stderr**; exits 3 for `ValidationError`, 1 otherwise.
  - `_output.handle_errors(fn)` — decorator wrapping a command body: catches `V2APIError` → `fail`.
  - `_context.get_client() -> Client` — env/credentials-file resolution (delegated to `Client()`); config errors exit 1 with the same stderr JSON shape.
  - Exit-code contract: 0 success, 1 API/config error, 2 usage (typer's default), 3 validation.

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/cli/test_output.py`:

```python
import json

import pytest
import typer

from extralit.v2._api._errors import V2APIError, ValidationError
from extralit.v2.cli._output import emit, fail, to_jsonable
from extralit.v2.models import SearchPage


def test_to_jsonable_handles_models_lists_dicts():
    page = SearchPage(items=[], total=3)
    assert to_jsonable(page) == {"items": [], "total": 3}
    assert to_jsonable([page]) == [{"items": [], "total": 3}]
    assert to_jsonable({"a": 1}) == {"a": 1}


def test_emit_json_when_flag_set(capsys):
    emit({"a": 1}, json_flag=True)
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_emit_json_when_not_a_tty(capsys):
    emit({"a": 1}, json_flag=False)  # pytest capture is not a tty -> auto-JSON
    assert json.loads(capsys.readouterr().out) == {"a": 1}


def test_fail_validation_exits_3_with_stderr_json(capsys):
    with pytest.raises(typer.Exit) as excinfo:
        fail(ValidationError(422, "bad value"))
    assert excinfo.value.exit_code == 3
    err = json.loads(capsys.readouterr().err)
    assert err["error"]["status"] == 422 and err["error"]["type"] == "ValidationError"


def test_fail_api_error_exits_1(capsys):
    with pytest.raises(typer.Exit) as excinfo:
        fail(V2APIError(500, "kaboom"))
    assert excinfo.value.exit_code == 1
    assert json.loads(capsys.readouterr().err)["error"]["detail"] == "kaboom"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/cli/test_output.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2.cli'`

- [ ] **Step 3: Implement**

`src/extralit/v2/cli/_output.py`:

```python
from __future__ import annotations

import functools
import json
import sys
from typing import Any

import typer

from extralit.v2._api._errors import V2APIError, ValidationError


def to_jsonable(data: Any) -> Any:
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [to_jsonable(item) for item in data]
    if isinstance(data, dict):
        return {key: to_jsonable(value) for key, value in data.items()}
    return data


def emit(data: Any, json_flag: bool) -> None:
    """JSON-first: --json forces JSON; a non-TTY stdout (pipes, agents, CI) defaults to it.
    Humans at a terminal get Rich output."""
    if json_flag or not sys.stdout.isatty():
        typer.echo(json.dumps(to_jsonable(data), default=str))
        return
    from rich.console import Console  # lazy: JSON path must not pay for rich

    Console().print(to_jsonable(data))


def fail(error: Exception) -> None:
    status = getattr(error, "status_code", None)
    payload = {"error": {"type": type(error).__name__, "status": status, "detail": str(getattr(error, "detail", error))}}
    typer.echo(json.dumps(payload, default=str), err=True)
    raise typer.Exit(code=3 if isinstance(error, ValidationError) else 1)


def handle_errors(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except V2APIError as error:
            fail(error)

    return wrapper
```

`src/extralit/v2/cli/_context.py`:

```python
from __future__ import annotations

from extralit.v2._sync import Client
from extralit.v2.cli._output import fail


def get_client() -> Client:
    """Non-interactive by construction: args come from env or the credentials file;
    a missing configuration is a structured error, never a prompt."""
    try:
        return Client()
    except ValueError as error:
        fail(error)
        raise  # unreachable; keeps type-checkers happy
```

`src/extralit/v2/cli/__init__.py` (placeholder for now; Task 12 fills in `add_v2_commands`):

```python
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/cli/test_output.py -v --disable-warnings`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/cli tests/unit/v2/cli
git commit -m "feat(sdk-v2): CLI JSON-first output helpers and error contract"
```

---

### Task 12: CLI `schemas` verbs + top-level takeover in app.py

**Files:**
- Create: `src/extralit/v2/cli/schemas.py`, `tests/unit/v2/cli/test_cli_schemas.py`
- Modify: `src/extralit/v2/cli/__init__.py`, `src/extralit/cli/app.py`

**Interfaces:**
- Consumes: `get_client`, `emit`, `handle_errors` (Task 11); `Client.schemas` methods (Tasks 5/10).
- Produces:
  - `extralit.v2.cli.schemas.app` — typer app with commands `list`, `get`, `create`, `publish`, `versions`.
  - `extralit.v2.cli.add_v2_commands(app: typer.Typer) -> None` — registers all v2 verb groups at top level (this task: `schemas`; Task 13/14 extend it).
  - `cli/app.py` no longer registers the v1 `schemas` subcommand; it calls `add_v2_commands(app)` instead.

- [ ] **Step 1: Check v1 schemas CLI is safe to unregister**

```bash
grep -rn "cli.schemas\|cli import schemas\|from extralit.cli.schemas" src/ tests/ --include="*.py" | grep -v "src/extralit/cli/schemas/"
```

Expected: hits only in `src/extralit/cli/app.py` and old tests (`tests/unit/cli/test_cli_schemas.py`). If another module (e.g. `cli/extraction`) imports from `extralit.cli.schemas`, keep the module files (we only unregister the subcommand) — that is the default posture anyway: **unregister, don't delete**.

- [ ] **Step 2: Write the failing tests**

`tests/unit/v2/cli/test_cli_schemas.py`:

```python
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

import extralit.v2.cli._context as context_mod
from extralit.v2._api._errors import ValidationError
from extralit.v2.cli.schemas import app
from extralit.v2.models import Schema

runner = CliRunner()  # click >= 8.2: stderr is separated by default (mix_stderr was removed)
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _schema(name="trials"):
    return Schema.model_validate(
        {
            "id": str(uuid.uuid4()), "name": name, "status": "draft", "current_version_id": None,
            "settings": {}, "workspace_id": WS, "inserted_at": NOW, "updated_at": NOW,
        }
    )


class FakeClient(SimpleNamespace):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


@pytest.fixture
def fake_client(monkeypatch):
    client = FakeClient(schemas=SimpleNamespace(list=lambda workspace_id: [_schema()]))
    monkeypatch.setattr(context_mod, "get_client", lambda: client)
    # schemas.py imports get_client at call time via the module attribute:
    import extralit.v2.cli.schemas as schemas_mod

    monkeypatch.setattr(schemas_mod, "get_client", lambda: client)
    return client


def test_list_emits_json(fake_client):
    result = runner.invoke(app, ["list", "--workspace-id", WS, "--json"])
    assert result.exit_code == 0
    items = json.loads(result.stdout)
    assert items[0]["name"] == "trials"


def test_validation_error_exits_3(fake_client):
    def boom(workspace_id):
        raise ValidationError(422, "bad")

    fake_client.schemas.list = boom
    result = runner.invoke(app, ["list", "--workspace-id", WS, "--json"])
    assert result.exit_code == 3
    assert json.loads(result.stderr)["error"]["type"] == "ValidationError"


def test_top_level_registration():
    from extralit.cli.app import app as root_app

    names = [t.name for t in root_app.registered_groups]
    # Task 14 Step 4 extends this tuple to all six verbs once they exist:
    # ("schemas", "records", "questions", "suggestions", "projection", "references")
    for verb in ("schemas",):
        assert verb in names, f"{verb} not registered at top level"
    assert names.count("schemas") == 1, "v1 schemas subcommand must be unregistered"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/cli/test_cli_schemas.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2.cli.schemas'`

- [ ] **Step 4: Implement**

`src/extralit/v2/cli/schemas.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Manage v2 schemas (Pandera, versioned)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("list")
@handle_errors
def list_schemas(
    workspace_id: str = typer.Option(..., "--workspace-id", help="Workspace UUID"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.schemas.list(UUID(workspace_id)), json_flag)


@app.command("get")
@handle_errors
def get_schema(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.schemas.get(UUID(schema_id)), json_flag)


@app.command("create")
@handle_errors
def create_schema(
    name: str = typer.Argument(...),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    settings: Optional[str] = typer.Option(None, "--settings", help="Settings as a JSON object"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.schemas.create(UUID(workspace_id), name, settings=json.loads(settings) if settings else None),
            json_flag,
        )


@app.command("publish")
@handle_errors
def publish_version(
    schema_id: str = typer.Argument(...),
    file: Path = typer.Option(..., "--file", help="Pandera DataFrameSchema JSON (schema.to_json() output)"),
    review_widgets: Optional[str] = typer.Option(None, "--review-widgets", help="JSON: {column: widget config}"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.schemas.publish(
                UUID(schema_id),
                file.read_text(),
                review_widgets=json.loads(review_widgets) if review_widgets else None,
            ),
            json_flag,
        )


@app.command("versions")
@handle_errors
def list_versions(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.schemas.versions(UUID(schema_id)), json_flag)
```

`src/extralit/v2/cli/__init__.py`:

```python
from __future__ import annotations

import typer


def add_v2_commands(app: typer.Typer) -> None:
    """Register v2 verbs at the TOP level of the extralit CLI (no `v2` prefix).
    v2 owns these names; the v1 `schemas` subcommand is deliberately replaced."""
    from extralit.v2.cli import schemas

    app.add_typer(schemas.app, name="schemas")
```

Modify `src/extralit/cli/app.py` — remove `schemas` from the v1 import list and its registration, add the v2 call:

```python
# In the import block at the top, DELETE the `schemas,` line:
from extralit.cli import (
    datasets,
    documents,
    extraction,
    files,
    info,
    login,
    logout,
    training,
    users,
    whoami,
    workflows,
    workspaces,
)


# In register_subcommands(), DELETE `app.add_typer(schemas.app, name="schemas")` and append:
def register_subcommands():
    app.add_typer(datasets.app, name="datasets")
    app.add_typer(documents.app, name="documents")
    app.add_typer(extraction.app, name="extraction")
    app.add_typer(files.app, name="files", hidden=True)
    app.add_typer(info.app, name="info")
    app.add_typer(login.app, name="login")
    app.add_typer(logout.app, name="logout")
    app.add_typer(training.app, name="training")
    app.add_typer(users.app, name="users")
    app.add_typer(whoami.app, name="whoami")
    app.add_typer(workflows.app, name="workflows")
    app.add_typer(workspaces.app, name="workspaces")

    # v2 owns the top-level verbs: schemas, records, questions, suggestions, projection, references.
    from extralit.v2.cli import add_v2_commands  # composition-root exception to the v1/v2 wall

    add_v2_commands(app)
```

Also delete or update the old v1 CLI test that asserts the v1 schemas commands exist (`tests/unit/cli/test_cli_schemas.py`): delete the file — the v1 subcommand is retired by design (spec §5).

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/cli/test_cli_schemas.py tests/unit/cli -v --disable-warnings`
Expected: new tests PASS; remaining v1 CLI tests PASS (no schemas registration asserted anywhere).

- [ ] **Step 6: Commit**

```bash
git add src/extralit/v2/cli src/extralit/cli/app.py tests/unit/v2/cli tests/unit/cli
git commit -m "feat(sdk-v2): top-level schemas CLI verbs replace v1 schemas subcommand"
```

---

### Task 13: CLI `records` and `questions` verbs (JSONL stdin piping)

**Files:**
- Create: `src/extralit/v2/cli/records.py`, `src/extralit/v2/cli/questions.py`, `tests/unit/v2/cli/test_cli_records.py`
- Modify: `src/extralit/v2/cli/__init__.py`

**Interfaces:**
- Consumes: Task 11 plumbing; `Client.records`/`Client.questions`.
- Produces:
  - `records` verbs: `upsert SCHEMA_ID [--file PATH|-] [--reference R]` (reads JSONL: one item per line), `search SCHEMA_ID [--text T] [--filter col:op:value ...] [--offset N] [--limit N]`, `list SCHEMA_ID [--status S] [--reference R] [--offset N] [--limit N]`, `delete SCHEMA_ID --ids id1,id2,...`
  - `questions` verbs: `list SCHEMA_ID`
  - `--filter` value syntax: `column:op:value` where `value` is JSON-decoded when possible (so `age:ge:18` → int 18; `label:in:["a","b"]` → list)

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/cli/test_cli_records.py`:

```python
import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from extralit.v2.cli.records import _parse_filter, app
from extralit.v2.models import Record, SearchPage

runner = CliRunner()  # click >= 8.2: stderr is separated by default (mix_stderr was removed)
SCHEMA_ID = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _record():
    return Record.model_validate(
        {
            "id": str(uuid.uuid4()), "schema_id": SCHEMA_ID, "schema_version_id": str(uuid.uuid4()),
            "reference": "10.1000/xyz", "external_id": None, "fields": {"size": "120"},
            "metadata": None, "status": "pending", "inserted_at": NOW, "updated_at": NOW,
        }
    )


class FakeClient(SimpleNamespace):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


@pytest.fixture
def fake_client(monkeypatch):
    calls = {}

    def upsert(schema_id, items, reference=None):
        calls["upsert"] = (schema_id, items, reference)
        return [_record()]

    def search(schema_id, text=None, filters=None, offset=0, limit=50):
        calls["search"] = (schema_id, text, filters, offset, limit)
        return SearchPage(items=[_record()], total=1)

    client = FakeClient(records=SimpleNamespace(bulk_upsert=upsert, search=search))
    import extralit.v2.cli.records as records_mod

    monkeypatch.setattr(records_mod, "get_client", lambda: client)
    return calls


def test_parse_filter_json_decodes_value():
    assert _parse_filter("age:ge:18") == ("age", "ge", 18)
    assert _parse_filter('label:in:["a","b"]') == ("label", "in", ["a", "b"])
    assert _parse_filter("country:eq:KE") == ("country", "eq", "KE")


def test_upsert_reads_jsonl_from_stdin(fake_client):
    lines = '{"size": "120"}\n{"size": "135"}\n'
    result = runner.invoke(app, ["upsert", SCHEMA_ID, "--reference", "10.1000/xyz"], input=lines)
    assert result.exit_code == 0, result.stderr
    schema_id, items, reference = fake_client["upsert"]
    assert items == [{"size": "120"}, {"size": "135"}]
    assert reference == "10.1000/xyz"
    assert json.loads(result.stdout)[0]["fields"] == {"size": "120"}


def test_search_passes_filters(fake_client):
    result = runner.invoke(
        app, ["search", SCHEMA_ID, "--text", "tumor", "--filter", "age:ge:18", "--limit", "10"]
    )
    assert result.exit_code == 0
    _, text, filters, _, limit = fake_client["search"]
    assert text == "tumor" and filters == [("age", "ge", 18)] and limit == 10
    assert json.loads(result.stdout)["total"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/cli/test_cli_records.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError: No module named 'extralit.v2.cli.records'`

- [ ] **Step 3: Implement**

`src/extralit/v2/cli/records.py`:

```python
from __future__ import annotations

import json
import sys
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Manage v2 records (schema-version-pinned, reference-keyed)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


def _parse_filter(raw: str) -> tuple:
    """col:op:value — value is JSON-decoded when possible ('age:ge:18' -> int 18)."""
    column, op, value = raw.split(":", 2)
    try:
        value = json.loads(value)
    except ValueError:
        pass  # keep as string
    return (column, op, value)


def _read_jsonl(file: Optional[str]) -> list[dict]:
    stream = sys.stdin if file in (None, "-") else open(file)
    try:
        return [json.loads(line) for line in stream if line.strip()]
    finally:
        if stream is not sys.stdin:
            stream.close()


@app.command("upsert")
@handle_errors
def upsert_records(
    schema_id: str = typer.Argument(...),
    file: Optional[str] = typer.Option(None, "--file", help="JSONL file of items; '-' or omitted reads stdin"),
    reference: Optional[str] = typer.Option(None, "--reference", help="Reference applied to items lacking one"),
    json_flag: bool = JSON_FLAG,
):
    items = _read_jsonl(file)
    with get_client() as client:
        emit(client.records.bulk_upsert(UUID(schema_id), items, reference=reference), json_flag)


@app.command("search")
@handle_errors
def search_records(
    schema_id: str = typer.Argument(...),
    text: Optional[str] = typer.Option(None, "--text"),
    filters: list[str] = typer.Option([], "--filter", help="col:op:value (op: eq|in|ge|le); repeatable"),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(50, "--limit"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.records.search(
                UUID(schema_id),
                text=text,
                filters=[_parse_filter(raw) for raw in filters],
                offset=offset,
                limit=limit,
            ),
            json_flag,
        )


@app.command("list")
@handle_errors
def list_records(
    schema_id: str = typer.Argument(...),
    status: Optional[str] = typer.Option(None, "--status"),
    reference: Optional[str] = typer.Option(None, "--reference"),
    offset: int = typer.Option(0, "--offset"),
    limit: int = typer.Option(50, "--limit"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(
            client.records.list(UUID(schema_id), status=status, reference=reference, offset=offset, limit=limit),
            json_flag,
        )


@app.command("delete")
@handle_errors
def delete_records(
    schema_id: str = typer.Argument(...),
    ids: str = typer.Option(..., "--ids", help="Comma-separated record ids"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        client.records.delete(UUID(schema_id), ids.split(","))
    emit({"deleted": len(ids.split(","))}, json_flag)
```

`src/extralit/v2/cli/questions.py`:

```python
from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Inspect v2 questions (column-bound)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("list")
@handle_errors
def list_questions(schema_id: str = typer.Argument(...), json_flag: bool = JSON_FLAG):
    with get_client() as client:
        emit(client.questions.list(UUID(schema_id)), json_flag)
```

Extend `src/extralit/v2/cli/__init__.py` `add_v2_commands`:

```python
    from extralit.v2.cli import questions, records, schemas

    app.add_typer(schemas.app, name="schemas")
    app.add_typer(records.app, name="records")
    app.add_typer(questions.app, name="questions")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/cli/test_cli_records.py -v --disable-warnings`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add src/extralit/v2/cli tests/unit/v2/cli/test_cli_records.py
git commit -m "feat(sdk-v2): records/questions CLI verbs with JSONL stdin piping"
```

---

### Task 14: CLI `suggestions`, `projection`, `references` verbs

**Files:**
- Create: `src/extralit/v2/cli/suggestions.py`, `src/extralit/v2/cli/projection.py`, `src/extralit/v2/cli/references.py`, `tests/unit/v2/cli/test_cli_annotation.py`
- Modify: `src/extralit/v2/cli/__init__.py`, `tests/unit/v2/cli/test_cli_schemas.py` (extend registration assertion)

**Interfaces:**
- Consumes: Task 11 plumbing; `Client.suggestions`/`Client.projections`/`Client.records.get_reference`.
- Produces:
  - `suggestions upsert RECORD_ID (--question-id UUID | --question NAME --schema-id UUID) --value JSON [--score F] [--agent A]`
  - `projection get REFERENCE --workspace-id UUID`
  - `references get REFERENCE --workspace-id UUID`
  - Final `add_v2_commands` registering all six verb groups.

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/cli/test_cli_annotation.py`:

```python
import json
import uuid
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from extralit.v2.cli.projection import app as projection_app
from extralit.v2.cli.suggestions import app as suggestions_app
from extralit.v2.models import ProjectionView

runner = CliRunner()  # click >= 8.2: stderr is separated by default (mix_stderr was removed)
RECORD_ID = str(uuid.uuid4())
Q_ID = str(uuid.uuid4())
WS = str(uuid.uuid4())


class FakeClient(SimpleNamespace):
    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        pass


def test_suggestions_upsert_decodes_json_value(monkeypatch):
    calls = {}

    def upsert(record, question, value, score=None, agent=None, schema_id=None):
        calls["args"] = (record, question, value, score, agent, schema_id)
        return SimpleNamespace(model_dump=lambda mode: {"ok": True})

    client = FakeClient(suggestions=SimpleNamespace(upsert=upsert))
    import extralit.v2.cli.suggestions as mod

    monkeypatch.setattr(mod, "get_client", lambda: client)
    result = runner.invoke(
        suggestions_app,
        ["upsert", RECORD_ID, "--question-id", Q_ID, "--value", '"120"', "--score", "0.9", "--agent", "claude"],
    )
    assert result.exit_code == 0, result.stderr
    record, question, value, score, agent, schema_id = calls["args"]
    assert (record, question, value, score, agent) == (RECORD_ID, Q_ID, "120", 0.9, "claude")


def test_suggestions_upsert_name_requires_schema_id(monkeypatch):
    import extralit.v2.cli.suggestions as mod

    monkeypatch.setattr(mod, "get_client", lambda: FakeClient(suggestions=SimpleNamespace()))
    result = runner.invoke(suggestions_app, ["upsert", RECORD_ID, "--question", "size", "--value", '"x"'])
    assert result.exit_code == 2  # usage error: --question needs --schema-id


def test_projection_get(monkeypatch):
    view = ProjectionView(reference="10.1000/j.abc", records=[], total_records=0)
    client = FakeClient(projections=SimpleNamespace(get=lambda ws, ref: view))
    import extralit.v2.cli.projection as mod

    monkeypatch.setattr(mod, "get_client", lambda: client)
    result = runner.invoke(projection_app, ["get", "10.1000/j.abc", "--workspace-id", WS])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["reference"] == "10.1000/j.abc"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/v2/cli/test_cli_annotation.py -v --disable-warnings`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`src/extralit/v2/cli/suggestions.py`:

```python
from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Write v2 suggestions (per record x question)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("upsert")
@handle_errors
def upsert_suggestion(
    record_id: str = typer.Argument(...),
    question_id: Optional[str] = typer.Option(None, "--question-id", help="Question UUID"),
    question: Optional[str] = typer.Option(None, "--question", help="Question NAME (needs --schema-id)"),
    schema_id: Optional[str] = typer.Option(None, "--schema-id", help="Schema UUID for name resolution"),
    value: str = typer.Option(..., "--value", help="Suggested value as JSON (e.g. '\"120\"' or '[1,2]')"),
    score: Optional[float] = typer.Option(None, "--score"),
    agent: Optional[str] = typer.Option(None, "--agent"),
    json_flag: bool = JSON_FLAG,
):
    if question_id is None and question is None:
        raise typer.BadParameter("pass --question-id or --question")
    if question is not None and question_id is None and schema_id is None:
        raise typer.BadParameter("--question (a name) requires --schema-id to resolve against")
    with get_client() as client:
        emit(
            client.suggestions.upsert(
                record_id,
                question_id or question,
                json.loads(value),
                score=score,
                agent=agent,
                schema_id=UUID(schema_id) if schema_id else None,
            ),
            json_flag,
        )
```

`src/extralit/v2/cli/projection.py`:

```python
from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Read v2 projections (response-or-suggestion per question)", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("get")
@handle_errors
def get_projection(
    reference: str = typer.Argument(..., help="Reference (DOI/URL/filename; slashes fine)"),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.projections.get(UUID(workspace_id), reference), json_flag)
```

`src/extralit/v2/cli/references.py`:

```python
from __future__ import annotations

from uuid import UUID

import typer

from extralit.v2.cli._context import get_client
from extralit.v2.cli._output import emit, handle_errors

app = typer.Typer(help="Cross-schema reference views", no_args_is_help=True)

JSON_FLAG = typer.Option(False, "--json", help="Force JSON output (auto when stdout is not a TTY)")


@app.command("get")
@handle_errors
def get_reference(
    reference: str = typer.Argument(..., help="Reference (DOI/URL/filename; slashes fine)"),
    workspace_id: str = typer.Option(..., "--workspace-id"),
    json_flag: bool = JSON_FLAG,
):
    with get_client() as client:
        emit(client.records.get_reference(UUID(workspace_id), reference), json_flag)
```

Final `src/extralit/v2/cli/__init__.py`:

```python
from __future__ import annotations

import typer


def add_v2_commands(app: typer.Typer) -> None:
    """Register v2 verbs at the TOP level of the extralit CLI (no `v2` prefix).
    v2 owns these names; the v1 `schemas` subcommand is deliberately replaced."""
    from extralit.v2.cli import projection, questions, records, references, schemas, suggestions

    app.add_typer(schemas.app, name="schemas")
    app.add_typer(records.app, name="records")
    app.add_typer(questions.app, name="questions")
    app.add_typer(suggestions.app, name="suggestions")
    app.add_typer(projection.app, name="projection")
    app.add_typer(references.app, name="references")
```

- [ ] **Step 4: Extend the registration assertion in `tests/unit/v2/cli/test_cli_schemas.py`**

Update `test_top_level_registration` to loop over all six verbs: `("schemas", "records", "questions", "suggestions", "projection", "references")`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/v2/cli -v --disable-warnings`
Expected: all PASS, including the six-verb registration assertion.

- [ ] **Step 6: Commit**

```bash
git add src/extralit/v2/cli tests/unit/v2/cli
git commit -m "feat(sdk-v2): suggestions/projection/references CLI verbs complete the verb set"
```

---

### Task 15: Boundary, lazy-import, and startup gates + docs

**Files:**
- Create: `tests/unit/v2/test_boundaries.py`
- Modify: `extralit/CLAUDE.md` (component docs)

**Interfaces:**
- Consumes: the whole v2 package.
- Produces: CI-enforced guarantees — import wall, no heavy imports at v2 import time, CLI startup sanity.

- [ ] **Step 1: Write the failing tests**

`tests/unit/v2/test_boundaries.py`:

```python
import re
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parents[3] / "src" / "extralit"
V2 = SRC / "v2"

# The single allowed v1 import inside v2 (credentials helper outlives v1 retirement).
ALLOWED_V1_IMPORT = "extralit.client.login"
V1_IMPORT = re.compile(r"^\s*(?:from|import)\s+(extralit\.(?!v2\b)[\w.]*)", re.MULTILINE)
V2_IMPORT = re.compile(r"^\s*(?:from|import)\s+extralit\.v2[\w.]*", re.MULTILINE)


def test_v2_imports_no_v1_except_credentials():
    violations = []
    for path in V2.rglob("*.py"):
        if path.name == "_generated.py":
            continue
        for match in V1_IMPORT.finditer(path.read_text()):
            if match.group(1) != ALLOWED_V1_IMPORT:
                violations.append(f"{path.relative_to(SRC)}: {match.group(0).strip()}")
    assert not violations, f"v2 -> v1 imports outside the credentials exception:\n" + "\n".join(violations)


def test_v1_never_imports_v2_except_composition_root():
    violations = []
    for path in SRC.rglob("*.py"):
        if V2 in path.parents or path == SRC / "cli" / "app.py":
            continue
        if V2_IMPORT.search(path.read_text()):
            violations.append(str(path.relative_to(SRC)))
    assert not violations, f"v1 files importing v2 (only cli/app.py may):\n" + "\n".join(violations)


HEAVY = ("pandas", "pandera", "datasets", "huggingface_hub")


def _heavy_after(imports: str) -> set:
    code = (
        f"import sys; {imports}; "
        f"print(','.join(sorted(m for m in {HEAVY!r} if m in sys.modules)))"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    return set(filter(None, proc.stdout.strip().split(",")))


def test_v2_adds_no_heavy_imports():
    """Agents make many short CLI calls: importing extralit.v2 (incl. cli) must not add
    heavy modules beyond what `import extralit` (the v1 package init) already drags in.
    Delta-based on purpose: v1's own import weight is Phase 6 scope, measured at the
    baseline (today: datasets + huggingface_hub via extralit/__init__.py)."""
    baseline = _heavy_after("import extralit")
    with_v2 = _heavy_after("import extralit; import extralit.v2; import extralit.v2.cli")
    added = with_v2 - baseline
    assert not added, f"extralit.v2 import added heavy modules: {sorted(added)}"
```

- [ ] **Step 2: Run tests**

Run: `uv run pytest tests/unit/v2/test_boundaries.py -v --disable-warnings`
Expected: all 3 PASS immediately if Tasks 1–14 held the line; any failure names the violating file — fix it (usually a top-level heavy import that belongs inside a function).

- [ ] **Step 3: Measure CLI startup and record the number**

```bash
time uv run extralit schemas --help
uv run python -X importtime -c "import extralit.v2.cli" 2>&1 | tail -5
```

The spec budget is < 300 ms for the v2 path. Note: `extralit.cli.app` still imports the v1 modules eagerly — if total startup exceeds the budget because of *v1* imports, record the measured split in the commit message; the v2 side must stay clean (the `test_v2_import_is_light` gate), and v1 startup is Phase 6 scope.

- [ ] **Step 4: Full verification**

```bash
uv run pytest tests/unit -v --disable-warnings
uv run ruff check
uv run ruff format --check
```

Expected: all green.

- [ ] **Step 5: Update component docs**

Append to `extralit/CLAUDE.md` a short v2 section:

```markdown
## v2 SDK (`src/extralit/v2/`)

- Parallel package for `/api/v2` (schema-centric). Import wall: v2 imports nothing from v1
  except `extralit.client.login`; only `cli/app.py` imports v2 (composition root).
- Wire types are GENERATED: `_api/openapi.json` (server `openapi-dump` snapshot) ->
  `_api/_generated.py` via datamodel-codegen. Never hand-edit; regenerate with the command
  in `tests/unit/v2/test_contract.py` and keep both in sync (drift-gated).
- `AsyncClient` is the real client; `Client` is a mechanical sync facade (background-thread
  portal — works in Jupyter). CLI verbs register at TOP level (`extralit schemas|records|...`),
  JSON-first (`--json` or non-TTY), errors as JSON on stderr (exit 0/1/2/3).
```

- [ ] **Step 6: Commit**

```bash
git add tests/unit/v2/test_boundaries.py CLAUDE.md
git commit -m "test(sdk-v2): import-wall, lazy-import, and startup gates + docs"
```

---

## Deferred (from spec — do NOT implement in this plan)

Responses write (submit/draft/discard), DataFrame/parquet/HF export, `rebuild-index`/admin verbs, webhooks, span questions, v1 retirement of the remaining subcommands, live-stack integration test (needs seeded backend — reuse `extralit-frontend/e2e/v2/seed/` approach in a follow-up).
