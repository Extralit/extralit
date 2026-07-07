from extralit_server.enums import SchemaKind, SchemaStatus, V2RecordStatus


def test_schema_kind_values():
    assert SchemaKind.singleton == "singleton"
    assert SchemaKind.table == "table"
    assert {k.value for k in SchemaKind} == {"singleton", "table"}


def test_schema_status_values():
    assert SchemaStatus.draft == "draft"
    assert SchemaStatus.published == "published"
    assert {s.value for s in SchemaStatus} == {"draft", "published"}


def test_v2_record_status_values():
    assert V2RecordStatus.pending == "pending"
    assert V2RecordStatus.discarded == "discarded"
    assert {s.value for s in V2RecordStatus} == {"pending", "completed", "discarded"}
