import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from extralit.v2._api._transport import AsyncTransport
from extralit.v2.resources import Records

pytestmark = pytest.mark.asyncio

API = "http://test:6900"
SCHEMA_ID = str(uuid.uuid4())
WS = str(uuid.uuid4())
NOW = datetime.now(timezone.utc).isoformat()


def _record(i):
    return {
        "id": str(uuid.uuid4()),
        "schema_id": SCHEMA_ID,
        "schema_version_id": str(uuid.uuid4()),
        "reference": "10.1000/xyz",
        "external_id": str(i),
        "fields": {"size": str(i)},
        "metadata": None,
        "status": "pending",
        "inserted_at": NOW,
        "updated_at": NOW,
    }


@pytest_asyncio.fixture
async def records():
    transport = AsyncTransport(API, api_key="k")
    r = Records(transport)
    yield r
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
    frame = pandas.DataFrame(
        [
            {"size": "120", "reference": "10.1000/a"},
            {"size": "135", "reference": "10.1000/b"},
        ]
    )
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
