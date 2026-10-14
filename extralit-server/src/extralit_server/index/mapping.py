"""Pure, I/O-free helpers mapping schema columns and records to a Lance row layout.

No LanceDB, DB, or object-store access — given a column manifest (the list of column
dicts derived from a schema version's `Field` rows) and a record, build the Arrow
schema and row dicts the LanceDB index engine writes (see ENG-36 for wiring this engine
in as a `SearchEngine`). The Lance table for a schema is the union (superset) of columns
across its versions plus system/identity columns and a derived `text` column that
carries the BM25 full-text index.
"""

from typing import Any
from uuid import UUID

import pyarrow as pa

# Identity/system columns present in every schema's Lance table, independent of the
# user-defined columns. `text` is the concatenated string-cell blob the FTS index covers.
SYSTEM_FIELDS = ["record_id", "reference", "status", "external_id", "text"]

# Observed pandera 0.32 / pandas 3.0 `str(column.dtype)` values -> Arrow types.
# large_string is used for text so the FTS index has no 2GiB offset ceiling.
_ARROW_BY_DTYPE = {
    "string[pyarrow]": pa.large_string(),
    "string": pa.large_string(),
    "object": pa.large_string(),
    "int64": pa.int64(),
    "int32": pa.int32(),
    "float64": pa.float64(),
    "float32": pa.float32(),
    "bool": pa.bool_(),
    "boolean": pa.bool_(),
    "datetime64[ns]": pa.timestamp("ns"),
}

# Column dtypes we treat as full-text material for the `text` blob.
_STRING_DTYPES = {"string[pyarrow]", "string", "object"}


def table_name_for(schema_id: UUID) -> str:
    """Lance table name for a schema. UUID hex (no dashes) is a safe identifier."""
    return f"schema_{schema_id.hex}"


def arrow_type_for(dtype: str) -> pa.DataType:
    """Map a pandera/pandas dtype string to an Arrow type; unknown -> large_string."""
    return _ARROW_BY_DTYPE.get(dtype, pa.large_string())


def union_columns(caches: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Union column entries across versions, first occurrence wins, order preserved."""
    seen: dict[str, dict[str, Any]] = {}
    for cache in caches:
        for column in cache or []:
            name = column["name"]
            if name not in seen:
                seen[name] = column
    return list(seen.values())


def arrow_schema_for(columns: list[dict[str, Any]]) -> pa.Schema:
    """Build the full Arrow schema: system fields + one typed field per schema column.

    All fields are nullable in Lance regardless of the Pandera `nullable` flag —
    Postgres enforces validation; the index must hold superset rows where older-version
    records legitimately lack newer columns.

    Raises ValueError if any user column name collides with a system field, since such
    a collision would produce a duplicate Arrow field or silently overwrite system data.
    """
    _system = set(SYSTEM_FIELDS)
    collisions = [c["name"] for c in columns if c["name"] in _system]
    if collisions:
        raise ValueError(
            f"Schema column name(s) collide with reserved system fields: {collisions}. Reserved names: {SYSTEM_FIELDS}"
        )
    fields = [
        pa.field("record_id", pa.large_string()),
        pa.field("reference", pa.large_string()),
        pa.field("status", pa.large_string()),
        pa.field("external_id", pa.large_string()),
    ]
    for column in columns:
        fields.append(pa.field(column["name"], arrow_type_for(column["dtype"])))
    fields.append(pa.field("text", pa.large_string()))
    return pa.schema(fields)


def concat_text(fields: dict[str, Any], columns: list[dict[str, Any]]) -> str:
    """Concatenate string-typed cells into a `col: value` blob for the FTS index."""
    lines = []
    for column in columns:
        if column["dtype"] not in _STRING_DTYPES:
            continue
        value = fields.get(column["name"])
        if value is None:
            continue
        lines.append(f"{column['name']}: {value}")
    return "\n".join(lines)


def record_to_row(record: Any, columns: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a Lance row dict for a record against the table's column superset.

    Every field in `arrow_schema_for(columns)` is present as a key; schema columns the
    record does not carry are filled with None (older-version rows in an evolved table).
    Permissive extra fields in `record.fields` that are not schema columns are ignored.
    UUID/enum system values are stringified to match the Arrow schema.
    """
    fields = record.fields or {}
    row: dict[str, Any] = {
        "record_id": str(record.id),
        "reference": record.reference,
        "status": record.status.value if hasattr(record.status, "value") else str(record.status),
        "external_id": record.external_id,
    }
    for column in columns:
        row[column["name"]] = fields.get(column["name"])
    row["text"] = concat_text(fields, columns)
    return row
