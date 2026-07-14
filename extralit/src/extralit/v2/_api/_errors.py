from __future__ import annotations

from typing import Any


class V2APIError(Exception):
    """Base error for /api/v2 calls."""

    def __init__(self, status_code: int, detail: Any = None):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail!r}")


class AuthError(V2APIError):
    """401/403, raised after any transparent token refresh has already been attempted."""


class NotFoundError(V2APIError):
    """404."""


class ValidationError(V2APIError):
    """422. The server emits two body shapes (detail: str | list[{loc, msg}]); `.errors` is normalized."""

    def __init__(self, status_code: int, detail: Any = None):
        super().__init__(status_code, detail)
        self.errors = normalize_validation_detail(detail)


def normalize_validation_detail(detail: Any) -> list[dict]:
    if detail is None:
        return []
    if isinstance(detail, str):
        return [{"loc": [], "msg": detail}]
    if isinstance(detail, list):
        out = []
        for item in detail:
            if isinstance(item, dict):
                out.append({"loc": list(item.get("loc", [])), "msg": str(item.get("msg", item))})
            else:
                out.append({"loc": [], "msg": str(item)})
        return out
    return [{"loc": [], "msg": str(detail)}]


def error_from_response(status_code: int, body: Any) -> V2APIError:
    detail = body.get("detail") if isinstance(body, dict) else body
    if status_code in (401, 403):
        return AuthError(status_code, detail)
    if status_code == 404:
        return NotFoundError(status_code, detail)
    if status_code == 422:
        return ValidationError(status_code, detail)
    return V2APIError(status_code, detail)
