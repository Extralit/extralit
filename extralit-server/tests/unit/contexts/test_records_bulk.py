# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.api.schemas.v1.records import RecordUpsert
from extralit_server.api.schemas.v1.records_bulk import RecordsBulkUpsert
from extralit_server.contexts.records_bulk import UpsertRecordsBulk
from extralit_server.enums import DatasetStatus
from extralit_server.models import Record
from extralit_server.search_engine import SearchEngine
from tests.factories import DatasetFactory, RecordFactory, TextFieldFactory


class TestUpsertRecordsBulk:
    async def test_upsert_records_bulk_with_existing_external_id(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        """Tests that records with existing external_id are updated instead of creating duplicates."""
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)
        await TextFieldFactory.create(name="text-field", dataset=dataset)

        # Create initial record with external_id
        await RecordFactory.create(fields={"text-field": "original value"}, external_id="existing-id", dataset=dataset)

        # Verify we have 1 record initially
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Create UpsertRecordsBulk instance
        upsert_bulk = UpsertRecordsBulk(db, mock_search_engine)

        # Upsert record with same external_id (should update existing record)
        bulk_upsert = RecordsBulkUpsert(
            items=[
                RecordUpsert(external_id="existing-id", fields={"text-field": "updated value"}),
            ]
        )

        await upsert_bulk.upsert_records_bulk(dataset, bulk_upsert)

        # Verify we still have only 1 record (existing record was updated)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Verify the record was updated
        record = (await db.execute(select(Record))).scalar_one()
        assert record.external_id == "existing-id"
        assert record.fields["text-field"] == "updated value"

    async def test_upsert_records_bulk_with_reference_metadata_external_id(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        """Tests that external_id from metadata (like reference field) is properly used for deduplication."""
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)
        await TextFieldFactory.create(name="text-field", dataset=dataset)

        # Create initial record with external_id from reference metadata
        await RecordFactory.create(
            fields={"text-field": "original value"},
            external_id="ref_123456",
            metadata_={"reference": "123456", "doi": "10.1000/sample"},
            dataset=dataset,
        )

        # Verify we have 1 record initially
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Create UpsertRecordsBulk instance
        upsert_bulk = UpsertRecordsBulk(db, mock_search_engine)

        # Attempt to upsert record with same external_id (simulating ImportHistory workflow)
        bulk_upsert = RecordsBulkUpsert(
            items=[
                RecordUpsert(
                    external_id="ref_123456",  # Same external_id generated from reference
                    fields={"text-field": "updated from import"},
                    metadata={"reference": "123456", "doi": "10.1000/sample", "pmid": "987654"},
                )
            ]
        )

        await upsert_bulk.upsert_records_bulk(dataset, bulk_upsert)

        # Verify we still have only 1 record (deduplication worked)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Verify the record was updated with new field and metadata
        record = (await db.execute(select(Record))).scalar_one()
        assert record.external_id == "ref_123456"
        assert record.fields["text-field"] == "updated from import"
        assert record.metadata_["reference"] == "123456"
        assert record.metadata_["pmid"] == "987654"  # New metadata added

    async def test_upsert_records_bulk_updates_existing_records_with_matching_external_id(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        """Tests that existing records with matching external_id have their fields updated from the upsert."""
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)
        await TextFieldFactory.create(name="title", dataset=dataset)
        await TextFieldFactory.create(name="content", dataset=dataset)

        # Create initial record
        original_record = await RecordFactory.create(
            fields={"title": "Original Title", "content": "Original Content"},
            external_id="update-test-123",
            metadata_={"source": "initial"},
            dataset=dataset,
        )

        # Store the original record ID and timestamps
        original_id = original_record.id
        original_inserted_at = original_record.inserted_at

        # Verify we have 1 record initially
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Create UpsertRecordsBulk instance
        upsert_bulk = UpsertRecordsBulk(db, mock_search_engine)

        # Upsert record with same external_id but different field values
        bulk_upsert = RecordsBulkUpsert(
            items=[
                RecordUpsert(
                    external_id="update-test-123",
                    fields={"title": "Updated Title", "content": "Updated Content"},
                    metadata={"source": "updated", "version": "2.0"},
                )
            ]
        )

        await upsert_bulk.upsert_records_bulk(dataset, bulk_upsert)

        # Verify we still have only 1 record (existing record was updated)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 1

        # Verify the same record was updated, not replaced
        updated_record = (await db.execute(select(Record))).scalar_one()
        assert updated_record.id == original_id  # Same record ID
        assert updated_record.external_id == "update-test-123"
        assert updated_record.inserted_at == original_inserted_at  # Insert time preserved
        assert updated_record.updated_at > original_inserted_at  # Update time changed

        # Verify field values were updated
        assert updated_record.fields["title"] == "Updated Title"
        assert updated_record.fields["content"] == "Updated Content"

        # Verify metadata was updated
        assert updated_record.metadata_["source"] == "updated"
        assert updated_record.metadata_["version"] == "2.0"

    async def test_upsert_records_bulk_preserves_different_external_ids(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        """Tests that records with different external_ids are both preserved."""
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)
        await TextFieldFactory.create(name="document", dataset=dataset)

        # Create initial records with different external_ids
        record_1 = await RecordFactory.create(fields={"document": "Document 1"}, external_id="doc_001", dataset=dataset)

        record_2 = await RecordFactory.create(fields={"document": "Document 2"}, external_id="doc_002", dataset=dataset)

        # Verify we have 2 records initially
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 2

        # Create UpsertRecordsBulk instance
        upsert_bulk = UpsertRecordsBulk(db, mock_search_engine)

        # Upsert with different external_ids (no conflicts)
        bulk_upsert = RecordsBulkUpsert(
            items=[
                RecordUpsert(
                    external_id="doc_003",  # New external_id
                    fields={"document": "Document 3"},
                ),
                RecordUpsert(
                    external_id="doc_001",  # Existing external_id (should update)
                    fields={"document": "Document 1 Updated"},
                ),
            ]
        )

        await upsert_bulk.upsert_records_bulk(dataset, bulk_upsert)

        # Verify we have 3 records total (1 new, 1 updated, 1 preserved)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 3

        # Get all records ordered by external_id
        records = (await db.execute(select(Record).order_by(Record.external_id))).scalars().all()

        # Verify doc_001 was updated
        assert records[0].external_id == "doc_001"
        assert records[0].fields["document"] == "Document 1 Updated"
        assert records[0].id == record_1.id  # Same record ID

        # Verify doc_002 was preserved unchanged
        assert records[1].external_id == "doc_002"
        assert records[1].fields["document"] == "Document 2"
        assert records[1].id == record_2.id  # Same record ID

        # Verify doc_003 was created as new record
        assert records[2].external_id == "doc_003"
        assert records[2].fields["document"] == "Document 3"
        assert records[2].id != record_1.id and records[2].id != record_2.id  # New record ID

    async def test_upsert_records_bulk_mixed_new_and_duplicate_external_ids(
        self, db: AsyncSession, mock_search_engine: SearchEngine
    ):
        """Tests handling of batch with both new external_ids and duplicate external_ids."""
        dataset = await DatasetFactory.create(status=DatasetStatus.ready)
        await TextFieldFactory.create(name="title", dataset=dataset)

        # Create initial records
        existing_record_1 = await RecordFactory.create(
            fields={"title": "Existing Paper 1"},
            external_id="paper_001",
            metadata_={"reference": "001"},
            dataset=dataset,
        )

        existing_record_2 = await RecordFactory.create(
            fields={"title": "Existing Paper 2"},
            external_id="paper_002",
            metadata_={"reference": "002"},
            dataset=dataset,
        )

        # Verify we have 2 records initially
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 2

        # Create UpsertRecordsBulk instance
        upsert_bulk = UpsertRecordsBulk(db, mock_search_engine)

        # Upsert batch with mix of new, duplicate, and updating external_ids
        bulk_upsert = RecordsBulkUpsert(
            items=[
                RecordUpsert(
                    external_id="paper_003",  # New external_id
                    fields={"title": "New Paper 3"},
                    metadata={"reference": "003"},
                ),
                RecordUpsert(
                    external_id="paper_001",  # Existing external_id (update)
                    fields={"title": "Updated Paper 1"},
                    metadata={"reference": "001", "updated": True},
                ),
                RecordUpsert(
                    external_id="paper_004",  # Another new external_id
                    fields={"title": "New Paper 4"},
                    metadata={"reference": "004"},
                ),
            ]
        )

        await upsert_bulk.upsert_records_bulk(dataset, bulk_upsert)

        # Verify final record count: 2 existing + 2 new = 4 total
        # (paper_001 updated, paper_002 unchanged, paper_003 and paper_004 new)
        assert (await db.execute(select(func.count(Record.id)))).scalar_one() == 4

        # Get all records ordered by external_id
        records = (await db.execute(select(Record).order_by(Record.external_id))).scalars().all()

        # Verify paper_001 was updated
        assert records[0].external_id == "paper_001"
        assert records[0].fields["title"] == "Updated Paper 1"
        assert records[0].metadata_["updated"] is True
        assert records[0].id == existing_record_1.id  # Same record ID

        # Verify paper_002 was unchanged (not in upsert batch)
        assert records[1].external_id == "paper_002"
        assert records[1].fields["title"] == "Existing Paper 2"
        assert records[1].id == existing_record_2.id  # Same record ID

        # Verify paper_003 was created as new record
        assert records[2].external_id == "paper_003"
        assert records[2].fields["title"] == "New Paper 3"
        assert records[2].metadata_["reference"] == "003"

        # Verify paper_004 was created as new record
        assert records[3].external_id == "paper_004"
        assert records[3].fields["title"] == "New Paper 4"
        assert records[3].metadata_["reference"] == "004"
