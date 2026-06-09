import json
import uuid

import pytest

import extralit as ex
from extralit.records._resource import Record


@pytest.fixture
def record():
    return ex.Record(
        id=uuid.uuid4(),
        fields={"text": "Hello World, how are you?"},
        suggestions=[
            ex.Suggestion("label", "positive", score=0.9),
            ex.Suggestion("topics", ["topic1", "topic2"], score=[0.9, 0.8]),
        ],
        responses=[ex.Response("label", "positive", user_id=uuid.uuid4())],
        metadata={"source": "twitter", "language": "en"},
        vectors={"text": [0, 0, 0]},
    )


def test_export_record_to_from_dict(record):
    record_dict = record.to_dict()
    imported_record = ex.Record.from_dict(record_dict)

    assert record.responses["label"][0].value == imported_record.responses["label"][0].value
    assert record.suggestions["topics"].value == imported_record.suggestions["topics"].value
    for key, value in record.metadata.items():
        assert imported_record.metadata[key] == value
    assert record.fields["text"] == imported_record.fields["text"]
    # This is a consequence of how UUIDs are treated in python and could be
    #  problematic for users.
    assert str(record.id) == imported_record.id


def test_export_generic_io_via_json(record):
    record_dict = record.to_dict()
    record_dict = json.dumps(record_dict)
    record_dict = json.loads(record_dict)
    imported_record = Record.from_dict(record_dict)

    assert record.responses["label"][0].value == imported_record.responses["label"][0].value
    assert record.suggestions["topics"].value == imported_record.suggestions["topics"].value
    for key, value in record.metadata.items():
        assert imported_record.metadata[key] == value
    assert record.fields["text"] == imported_record.fields["text"]
    assert record.vectors["text"] == imported_record.vectors["text"]
