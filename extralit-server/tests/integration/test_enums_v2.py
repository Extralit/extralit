from extralit_server.enums import SchemaStatus, V2RecordStatus


def test_schema_status_values():
    assert SchemaStatus.draft == "draft"
    assert SchemaStatus.published == "published"
    assert {s.value for s in SchemaStatus} == {"draft", "published"}


def test_v2_record_status_values():
    assert V2RecordStatus.pending == "pending"
    assert V2RecordStatus.discarded == "discarded"
    assert {s.value for s in V2RecordStatus} == {"pending", "completed", "discarded"}
