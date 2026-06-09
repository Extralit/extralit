from extralit.records import Filter


class TestFilters:
    def test_filter_by_responses_status(self):
        test_filter = Filter(("response.status", "in", ["submitted", "discard"]))
        assert test_filter.api_model().model_dump(by_alias=True) == {
            "type": "and",
            "and": [
                {
                    "scope": {"entity": "response", "property": "status", "question": None},
                    "type": "terms",
                    "values": ["submitted", "discard"],
                }
            ],
        }
