from extralit_server.api.schemas.v1.records import RecordUpsert


class TestRecordUpsert:
    def test_record_upsert_without_fields(self):
        record_upsert = RecordUpsert()

        assert record_upsert.fields is None
