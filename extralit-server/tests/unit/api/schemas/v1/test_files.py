import pytest
from pydantic import ValidationError

from extralit_server.api.schemas.v1.files import FileObjectResponse, ObjectMetadata


class _StreamingChecksumBodyLike:
    """Stand-in for aiobotocore's StreamingChecksumBody / StreamingBody.

    The concrete S3 body type is not a urllib3 HTTPResponse; consumers only ever
    ``await .response.read()``. This is what the field must accept.
    """

    def __init__(self, content: bytes) -> None:
        self._content = content

    async def read(self, amt: int | None = None) -> bytes:
        return self._content


def _metadata() -> ObjectMetadata:
    return ObjectMetadata(workspace="b", object_name="o")


def test_accepts_non_urllib3_streaming_body():
    # Regression: aiobotocore returns StreamingChecksumBody, not urllib3.HTTPResponse.
    # A strict annotation triggered pydantic is_instance_of 422s on every v2 upsert.
    body = _StreamingChecksumBodyLike(b"payload")
    resp = FileObjectResponse(response=body, metadata=_metadata(), versions=None)
    assert resp.response is body


def test_rejects_none_response():
    with pytest.raises(ValidationError):
        FileObjectResponse(response=None, metadata=_metadata(), versions=None)
