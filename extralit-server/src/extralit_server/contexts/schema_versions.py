"""Versioned, object-store-backed Pandera schema bodies for a dataset.

A dataset's record shape is declared by a Pandera schema whose body lives in the
workspace bucket. Publishing a version uploads the body, registers a `SchemaVersion`
pointer, and projects every declared column into a `Field` row -- so the `fields`
table is the queryable column manifest and there is no cached copy of it.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID

import pandera.pandas as pa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from extralit_server.contexts import files as files_ctx
from extralit_server.enums import FieldType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.database import Dataset, Field, SchemaVersion
from extralit_server.webhooks.v1.datasets import notify_dataset_event as notify_dataset_event_v1
from extralit_server.webhooks.v1.enums import DatasetEvent

if TYPE_CHECKING:
    from types_aiobotocore_s3.client import S3Client


def object_key_for(dataset_id: UUID, version: int) -> str:
    return f"schemas/{dataset_id}/v{version}.json"


def derive_column_fields(
    body_json: str, review_widgets: dict[str, dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Project a Pandera body into `Field` row payloads, one per declared column.

    `review_widgets` is the out-of-band per-column widget overlay: Pandera's `to_json`
    drops `Column.metadata`, so widget config cannot ride inside the body itself.
    """
    review_widgets = review_widgets or {}
    try:
        schema = pa.DataFrameSchema.from_json(body_json)
    except Exception as ex:
        raise UnprocessableEntityError(f"schema body is not a valid Pandera DataFrameSchema: {ex}") from ex

    return [
        {
            "name": name,
            "title": name,
            # A column is an ingestion input, never annotator-required.
            "required": False,
            "settings": {
                "type": FieldType.column,
                "dtype": str(column.dtype),
                "nullable": bool(column.nullable),
                "review": review_widgets.get(name),
            },
        }
        for name, column in schema.columns.items()
    ]


async def _next_version_number(db: AsyncSession, dataset_id: UUID) -> int:
    """Allocate the next version number, serializing concurrent publishes on PostgreSQL.

    The `SELECT ... FOR UPDATE` is what makes the allocation safe, and it must be held for
    the rest of the transaction. Without it two concurrent publishes read the same max and
    both derive the same `object_key` from it, so both `put_object` to the SAME key: the
    write that lands second overwrites the first's body even after the first publisher's
    `SchemaVersion` row -- carrying a checksum computed from its own body -- has committed.
    The committed row would then point at content that does not match its checksum, breaking
    the immutability this model exists to provide. The unique constraint alone does not save
    us: it fires at `db.flush()`, long after the object was overwritten.

    **The guarantee is PostgreSQL-only.** SQLAlchemy's SQLite dialect compiles the row lock
    away entirely -- the emitted SQL is a bare SELECT, not an error -- and pysqlite opens
    transactions DEFERRED, so a read takes no lock either. Two concurrent publishes on SQLite
    therefore still read the same max and still overwrite each other's object; the losing
    INSERT then fails on the unique constraint or with `database is locked`, by which point
    the object is already corrupt. SQLite is the default `database_url` (settings.py), so
    this is a real gap on a default deployment, not a test-only artifact -- it is simply not
    closed by this function. Closing it needs a dialect-conditional `BEGIN IMMEDIATE` (or
    moving allocation into the INSERT), deferred as its own design question -- see
    docs/superpowers/plans/2026-07-26-fold-followups.md.
    """
    await db.execute(select(Dataset.id).where(Dataset.id == dataset_id).with_for_update())

    stmt = select(SchemaVersion.version).where(SchemaVersion.dataset_id == dataset_id)
    return max((await db.execute(stmt)).scalars().all(), default=0) + 1


async def _reject_incompatible_columns(
    db: AsyncSession, dataset: Dataset, field_payloads: list[dict[str, Any]]
) -> None:
    """Reject a body that cannot be reconciled with the dataset's existing `Field` rows.

    Three rules, checked in one pass before any write so a rejected publish leaves behind
    neither a version row nor an S3 object:

    * A column must not collide with an annotation field. `Field.upsert_many` keys on
      `(name, dataset_id)`, so an upsert over a `text`/`image`/`chat`/`custom`/`table` field
      of the same name would rewrite its settings into a column -- silently dropping it from
      record value validation, since column fields are deliberately not value-validated.
    * A column's dtype is immutable once published, the same property LanceDB has.
    * A republish must not introduce a new column once the dataset is `ready`. The search
      index is created with `"dynamic": "strict"` on the draft -> ready transition and
      nothing evolves its mapping afterwards, so a new column would leave the dataset
      unwritable: the next record write carries `fields.<new_column>` into a strict index
      with no mapping for it and is rejected outright. Rejecting here keeps the failure at
      the call that caused it. Lifting this needs `put_mapping` on republish -- see
      docs/superpowers/plans/2026-07-26-fold-followups.md.
    """
    stmt = select(Field.name, Field.settings).where(Field.dataset_id == dataset.id)
    existing = dict((await db.execute(stmt)).all())

    for payload in field_payloads:
        name = payload["name"]
        settings = existing.get(name)

        if settings is None:
            if dataset.is_ready:
                raise UnprocessableEntityError(
                    f"column {name!r} cannot be added to a published dataset -- "
                    "the search index mapping is fixed when the dataset is published"
                )
            continue

        if settings.get("type") != FieldType.column:
            raise UnprocessableEntityError(
                f"column {name!r} collides with an existing {settings.get('type')} field of the same name"
            )

        existing_dtype = settings["dtype"]
        new_dtype = payload["settings"]["dtype"]
        if existing_dtype != new_dtype:
            raise UnprocessableEntityError(
                f"column {name!r} cannot change dtype from {existing_dtype!r} to {new_dtype!r} -- "
                "schema columns are immutable once published"
            )


async def publish_version(
    db: AsyncSession,
    s3_client: "S3Client",
    dataset: Dataset,
    *,
    body: str,
    bucket: str,
    review_widgets: dict[str, dict[str, Any]] | None = None,
    created_by: UUID | None = None,
) -> SchemaVersion:
    """Upload a body, register the version, and materialize its column fields."""
    # Parse and validate before any write so a rejected publish leaves no version row and
    # no S3 object.
    field_payloads = derive_column_fields(body, review_widgets)
    await _reject_incompatible_columns(db, dataset, field_payloads)

    next_version = await _next_version_number(db, dataset.id)
    key = object_key_for(dataset.id, next_version)
    metadata = await files_ctx.put_object(s3_client, bucket, key, body, content_type="application/json")

    parent_id = dataset.current_schema_version_id

    version = await SchemaVersion.create(
        db,
        dataset_id=dataset.id,
        version=next_version,
        object_key=key,
        object_version_id=getattr(metadata, "version_id", None),
        etag=metadata.etag,
        checksum=files_ctx.compute_hash(body.encode("utf-8")),
        parent_version_id=parent_id,
        created_by=created_by,
        autocommit=False,
    )
    # Flush so `version.id` (a flush-time default) exists before `datasets` points at it.
    # Doing both in one flush would form a datasets<->schema_versions FK cycle.
    await db.flush()

    if field_payloads:
        # `Field.upsert_many` raises on an empty `objects` list (models/mixins.py); a
        # column-less Pandera body is a legal, if degenerate, schema, so skip rather
        # than reject -- a business rule shouldn't hinge on a persistence-layer guard.
        await Field.upsert_many(
            db,
            objects=[{**payload, "dataset_id": dataset.id} for payload in field_payloads],
            constraints=[Field.name, Field.dataset_id],
            autocommit=False,
        )

    # Publishing a schema version deliberately does NOT publish the dataset:
    # `PUT /datasets/{id}/publish` stays the sole draft -> ready transition, and so the sole
    # caller of `create_index`. A schema-backed dataset therefore gets the same lifecycle and
    # the same `DatasetPublishValidator` checks as an annotation one, and its questions can be
    # created -- column bindings and all -- after the columns exist and before it is published.
    await dataset.update(db, current_schema_version_id=version.id, autocommit=False)
    await db.commit()

    # A schema version is a dataset mutation, so it gets `updated` -- the same event
    # contexts/datasets.py::update_dataset fires for any other attribute change. `published`
    # belongs to publish_dataset alone.
    await notify_dataset_event_v1(db, DatasetEvent.updated, dataset)

    return version


async def list_versions(db: AsyncSession, dataset: Dataset) -> list[SchemaVersion]:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset.id).order_by(SchemaVersion.version)
    return list((await db.execute(stmt)).scalars().all())


async def get_version_by_number(db: AsyncSession, dataset_id: UUID, version: int) -> SchemaVersion | None:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset_id, SchemaVersion.version == version)
    return (await db.execute(stmt)).scalar_one_or_none()
