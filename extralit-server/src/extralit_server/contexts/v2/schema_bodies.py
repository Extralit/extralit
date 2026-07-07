"""Pure helpers for working with a Pandera DataFrameSchema body (JSON).

No DB or object-store access — given a schema body string, derive a denormalized
column cache and validate a single record's `fields` dict against it.

Two installed-version realities shape this module (see spec §13):

* Pandera 0.32 drops per-`Column.metadata` through ``to_json``/``from_json``, so the
  per-column review widget cannot live inside the body. It is carried out-of-band in a
  ``review_widgets`` side map (column name -> widget config) and merged here.
* ``pa.Int`` maps to numpy ``int64``, which cannot hold ``None``. A null in a nullable
  Int column therefore fails dtype coercion, so ``validate_record_fields`` validates only
  the non-null fields and re-attaches nulls as ``None``.
"""

import math
from typing import Any

import pandas as pd
import pandera.pandas as pa


class SchemaValidationError(Exception):
    """Raised when a record's fields fail Pandera validation."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(f"Record failed schema validation with {len(errors)} error(s)")


def _load(body_json: str) -> pa.DataFrameSchema:
    return pa.DataFrameSchema.from_json(body_json)


def _is_null(value: Any) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def derive_columns_cache(
    body_json: str, review_widgets: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Return one entry per column: name, dtype, nullable, and optional review widget.

    The Pandera body is the source of truth for name/dtype/nullable. The per-column
    ``review`` widget is taken from the ``review_widgets`` side map (column name ->
    widget config); if a column is absent from the map its ``review`` is ``None``.
    """
    review_widgets = review_widgets or {}
    schema = _load(body_json)
    cache: list[dict[str, Any]] = []
    for name, column in schema.columns.items():
        cache.append(
            {
                "name": name,
                "dtype": str(column.dtype),
                "nullable": bool(column.nullable),
                "review": review_widgets.get(name),
            }
        )
    return cache


def validate_record_fields(body_json: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Validate+coerce a single record's fields against the schema body.

    Returns the coerced single-row mapping with native JSON types (no numpy scalars),
    nulls preserved as ``None``. Raises ``SchemaValidationError`` with a list of
    ``{column, check, error}`` dicts on failure.
    """
    schema = _load(body_json)
    errors: list[dict[str, Any]] = []

    null_fields: dict[str, None] = {}
    non_null: dict[str, Any] = {}
    for name, value in fields.items():
        if _is_null(value):
            column = schema.columns.get(name)
            if column is not None and not column.nullable:
                errors.append({"column": name, "check": "not_nullable", "error": "null value not allowed"})
            null_fields[name] = None
        else:
            non_null[name] = value

    # A required (non-nullable) column entirely omitted from `fields` is a violation too —
    # not just one explicitly set to null.
    for name, column in schema.columns.items():
        if not column.nullable and name not in fields:
            errors.append({"column": name, "check": "missing", "error": "required column missing"})

    coerced: dict[str, Any] = {}
    present_columns = {name: col for name, col in schema.columns.items() if name in non_null}
    if present_columns:
        sub_schema = pa.DataFrameSchema(present_columns, coerce=True)
        frame = pd.DataFrame([{name: non_null[name] for name in present_columns}])
        try:
            validated = sub_schema.validate(frame, lazy=True)
        except pa.errors.SchemaErrors as exc:
            for row in exc.failure_cases.to_dict(orient="records"):
                errors.append(
                    {
                        "column": row.get("column"),
                        "check": row.get("check"),
                        "error": str(row.get("failure_case")),
                    }
                )
            raise SchemaValidationError(errors) from exc
        # Convert numpy scalars to native python types for the record.fields JSONB column.
        coerced = _row_to_native(validated)

    if errors:
        raise SchemaValidationError(errors)

    # Non-schema fields that were non-null but absent from the schema fall through as-is.
    extras = {name: value for name, value in non_null.items() if name not in present_columns}
    return {**coerced, **extras, **null_fields}


def _row_to_native(frame: pd.DataFrame) -> dict[str, Any]:
    """Convert the single validated row to native, JSON-serializable python types.

    Avoids the lossy ``DataFrame.to_json`` detour, which truncates floats to 10 decimal
    places and serializes datetimes as deprecated epoch integers. numpy scalars become
    native python via ``.item()`` (exact for floats), Timestamps become ISO strings, and
    NaN/NaT become ``None``.

    Each cell is read per-column (``frame[col].iloc[0]``) rather than via ``frame.iloc[0]``:
    a row Series upcasts to the columns' common dtype, so an ``int64`` cell in a frame that
    also has a ``float64`` column would silently become a python ``float``.
    """
    out: dict[str, Any] = {}
    for col in frame.columns:
        value = frame[col].iloc[0]
        if pd.isna(value):
            out[col] = None
        elif isinstance(value, pd.Timestamp):
            out[col] = value.isoformat()
        elif hasattr(value, "item"):
            out[col] = value.item()
        else:
            out[col] = value
    return out
