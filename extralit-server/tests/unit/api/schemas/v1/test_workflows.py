from uuid import uuid4

import pytest
from pydantic import ValidationError

from extralit_server.api.schemas.v1.workflows import StartWorkflowRequest
from extralit_server.contexts.ocr.parsers import list_parsers


def _request(**overrides) -> StartWorkflowRequest:
    return StartWorkflowRequest(document_id=uuid4(), workspace_name="ws", **overrides)


class TestStartWorkflowRequest:
    def test_accepts_a_registered_parser(self):
        assert _request(layout_parser="pdf_inspector").layout_parser == "pdf_inspector"

    def test_omitting_the_parser_skips_layout_extraction(self):
        assert _request().layout_parser is None

    def test_rejects_an_unregistered_parser(self):
        with pytest.raises(ValidationError, match="unknown layout parser"):
            _request(layout_parser="marker")

    def test_error_lists_the_installed_parsers(self):
        with pytest.raises(ValidationError, match=str(list_parsers())):
            _request(layout_parser="marker")
