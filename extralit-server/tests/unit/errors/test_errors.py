from extralit_server.errors import GenericServerError


def test_generic_error():
    err = GenericServerError(error=ValueError("this is an error"))
    assert str(err) == "extralit.api.errors::GenericServerError(type=builtins.ValueError,message=this is an error)"
