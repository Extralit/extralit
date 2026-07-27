import pytest

from tests.factories import DatasetFactory, RecordFactory, TextFieldFactory


@pytest.mark.asyncio
class TestRecordReference:
    async def _ready_dataset(self):
        dataset = await DatasetFactory.create(status="ready")
        await TextFieldFactory.create(dataset=dataset, name="text")
        return dataset

    async def test_bulk_create_persists_reference(self, async_client, owner_auth_header, mock_search_engine, db):
        dataset = await self._ready_dataset()
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/records/bulk",
            headers=owner_auth_header,
            json={"items": [{"fields": {"text": "a"}, "reference": "10.1000/j.foo.2020.01"}]},
        )
        assert response.status_code == 201, response.json()
        assert response.json()["items"][0]["reference"] == "10.1000/j.foo.2020.01"

    async def test_reference_is_optional(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await self._ready_dataset()
        response = await async_client.post(
            f"/api/v1/datasets/{dataset.id}/records/bulk",
            headers=owner_auth_header,
            json={"items": [{"fields": {"text": "a"}}]},
        )
        assert response.status_code == 201
        assert response.json()["items"][0]["reference"] is None

    async def test_bulk_upsert_updates_reference(self, async_client, owner_auth_header, mock_search_engine, db):
        dataset = await self._ready_dataset()
        record = await RecordFactory.create(dataset=dataset, external_id="x1", reference="old")
        response = await async_client.put(
            f"/api/v1/datasets/{dataset.id}/records/bulk",
            headers=owner_auth_header,
            json={"items": [{"external_id": "x1", "reference": "new"}]},
        )
        assert response.status_code == 200, response.json()
        await db.refresh(record)
        assert record.reference == "new"

    async def test_bulk_upsert_leaves_reference_alone_when_omitted(
        self, async_client, owner_auth_header, mock_search_engine, db
    ):
        dataset = await self._ready_dataset()
        record = await RecordFactory.create(dataset=dataset, external_id="x1", reference="keep")
        await async_client.put(
            f"/api/v1/datasets/{dataset.id}/records/bulk",
            headers=owner_auth_header,
            json={"items": [{"external_id": "x1", "metadata": {"a": 1}}]},
        )
        await db.refresh(record)
        assert record.reference == "keep"

    async def test_list_records_filters_by_reference(self, async_client, owner_auth_header):
        dataset = await self._ready_dataset()
        await RecordFactory.create(dataset=dataset, reference="doi-a")
        await RecordFactory.create(dataset=dataset, reference="doi-b")
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/records?reference=doi-a", headers=owner_auth_header
        )
        assert response.status_code == 200
        assert [r["reference"] for r in response.json()["items"]] == ["doi-a"]

    async def test_patch_record_updates_reference(self, async_client, owner_auth_header, mock_search_engine, db):
        dataset = await self._ready_dataset()
        record = await RecordFactory.create(dataset=dataset, reference="old")
        response = await async_client.patch(
            f"/api/v1/records/{record.id}",
            headers=owner_auth_header,
            json={"reference": "new"},
        )
        assert response.status_code == 200, response.json()
        assert response.json()["reference"] == "new"
        await db.refresh(record)
        assert record.reference == "new"

    async def test_patch_record_leaves_reference_alone_when_omitted(
        self, async_client, owner_auth_header, mock_search_engine, db
    ):
        dataset = await self._ready_dataset()
        record = await RecordFactory.create(dataset=dataset, reference="keep")
        response = await async_client.patch(
            f"/api/v1/records/{record.id}",
            headers=owner_auth_header,
            json={"metadata": {"a": 1}},
        )
        assert response.status_code == 200, response.json()
        await db.refresh(record)
        assert record.reference == "keep"

    async def test_a_reference_may_contain_slashes(self, async_client, owner_auth_header, mock_search_engine):
        dataset = await self._ready_dataset()
        await async_client.post(
            f"/api/v1/datasets/{dataset.id}/records/bulk",
            headers=owner_auth_header,
            json={"items": [{"fields": {"text": "a"}, "reference": "10.1000/j.foo.2020.01"}]},
        )
        response = await async_client.get(
            f"/api/v1/datasets/{dataset.id}/records",
            headers=owner_auth_header,
            params={"reference": "10.1000/j.foo.2020.01"},
        )
        assert len(response.json()["items"]) == 1
