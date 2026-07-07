from extralit_server.enums import SchemaKind, SchemaStatus


def test_schema_kind_values():
    assert SchemaKind.singleton == "singleton"
    assert SchemaKind.table == "table"
    assert {k.value for k in SchemaKind} == {"singleton", "table"}


def test_schema_status_values():
    assert SchemaStatus.draft == "draft"
    assert SchemaStatus.published == "published"
    assert {s.value for s in SchemaStatus} == {"draft", "published"}
