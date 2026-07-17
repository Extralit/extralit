from extralit.v2._api._errors import (
    AuthError,
    NotFoundError,
    V2APIError,
    ValidationError,
    error_from_response,
    normalize_validation_detail,
)


def test_normalizes_string_detail():
    assert normalize_validation_detail("boom") == [{"loc": [], "msg": "boom"}]


def test_normalizes_fastapi_list_detail():
    detail = [{"loc": ["body", "items", 0, "reference"], "msg": "field required", "type": "missing"}]
    assert normalize_validation_detail(detail) == [{"loc": ["body", "items", 0, "reference"], "msg": "field required"}]


def test_normalizes_none_and_junk():
    assert normalize_validation_detail(None) == []
    assert normalize_validation_detail({"weird": 1}) == [{"loc": [], "msg": "{'weird': 1}"}]


def test_error_from_response_maps_statuses():
    assert isinstance(error_from_response(401, {"detail": "nope"}), AuthError)
    assert isinstance(error_from_response(403, {"detail": "nope"}), AuthError)
    assert isinstance(error_from_response(404, {"detail": "gone"}), NotFoundError)
    err = error_from_response(422, {"detail": "bad value"})
    assert isinstance(err, ValidationError)
    assert err.errors == [{"loc": [], "msg": "bad value"}]
    other = error_from_response(500, {"detail": "kaboom"})
    assert type(other) is V2APIError
    assert other.status_code == 500 and other.detail == "kaboom"


def test_error_from_response_non_dict_body():
    err = error_from_response(502, "<html>bad gateway</html>")
    assert err.detail == "<html>bad gateway</html>"
