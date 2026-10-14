import pytest

from extralit import Record, Suggestion
from extralit.records._resource import RecordSuggestions


@pytest.fixture
def record():
    return Record(fields={"name": "John Doe"}, metadata={"age": 30})


class TestRecordSuggestions:
    def test_create_record_suggestions(self, record: Record):
        suggestions = RecordSuggestions(
            suggestions=[
                Suggestion("name", "John Doe", score=0.9),
                Suggestion("label", ["A", "B"], score=[0.8, 0.9]),
            ],
            record=record,
        )

        assert suggestions.record == record
        assert suggestions["name"].value == "John Doe"
        assert suggestions["name"].score == 0.9
        assert suggestions["label"].value == ["A", "B"]
        assert suggestions["label"].score == [0.8, 0.9]
