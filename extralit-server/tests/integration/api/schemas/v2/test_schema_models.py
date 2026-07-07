from uuid import uuid4

from extralit_server.api.schemas.v2.schemas import SchemaCreate, SchemaVersionCreate
from extralit_server.enums import SchemaKind


def test_schema_create_defaults_settings_to_empty_dict():
    payload = SchemaCreate(name="population", kind=SchemaKind.table, workspace_id=uuid4())
    assert payload.settings == {}


def test_schema_version_create_requires_body():
    v = SchemaVersionCreate(body='{"columns": {}}')
    assert v.body.startswith("{")


def test_schema_version_create_defaults_review_widgets_to_empty_dict():
    v = SchemaVersionCreate(body='{"columns": {}}')
    assert v.review_widgets == {}
