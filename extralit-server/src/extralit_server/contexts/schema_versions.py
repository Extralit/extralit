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
from extralit_server.enums import DatasetStatus, FieldType
from extralit_server.errors.future import UnprocessableEntityError
from extralit_server.models.database import Dataset, Field, SchemaVersion
from extralit_server.search_engine import SearchEngine
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
    stmt = select(SchemaVersion.version).where(SchemaVersion.dataset_id == dataset_id)
    return max((await db.execute(stmt)).scalars().all(), default=0) + 1


async def _reject_dtype_changes(db: AsyncSession, dataset_id: UUID, field_payloads: list[dict[str, Any]]) -> None:
    """Enforce column dtype immutability: a republish may add new columns but must not change
    the dtype of a column that is already a `Field` -- schemas and column dtypes are immutable,
    the same property LanceDB has.

    Only checked against existing `column`-type fields. A Pandera column colliding by name with
    an existing `text`/`image`/`chat` field is a separate, deferred concern -- see
    docs/superpowers/plans/2026-07-26-fold-followups.md.
    """
    stmt = select(Field.name, Field.settings).where(Field.dataset_id == dataset_id)
    existing_column_dtypes = {
        name: field_settings["dtype"]
        for name, field_settings in (await db.execute(stmt)).all()
        if field_settings.get("type") == FieldType.column
    }

    for payload in field_payloads:
        name = payload["name"]
        if name not in existing_column_dtypes:
            continue

        existing_dtype = existing_column_dtypes[name]
        new_dtype = payload["settings"]["dtype"]
        if existing_dtype != new_dtype:
            raise UnprocessableEntityError(
                f"column {name!r} cannot change dtype from {existing_dtype!r} to {new_dtype!r} -- "
                "schema columns are immutable once published"
            )


async def publish_version(
    db: AsyncSession,
    search_engine: SearchEngine,
    s3_client: "S3Client",
    dataset: Dataset,
    *,
    body: str,
    bucket: str,
    review_widgets: dict[str, dict[str, Any]] | None = None,
    created_by: UUID | None = None,
) -> SchemaVersion:
    """Upload a body, register the version, materialize its column fields, publish the dataset."""
    # Parse before any write so an invalid body leaves no version row and no S3 object.
    field_payloads = derive_column_fields(body, review_widgets)

    # Reject dtype changes before any write too, for the same reason.
    await _reject_dtype_changes(db, dataset.id, field_payloads)

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

    # Captured before `dataset.update` flips `status` -- the webhook below must fire only on
    # the actual draft -> ready transition, not on every republish of an already-ready dataset.
    was_already_ready = dataset.is_ready

    await dataset.update(db, current_schema_version_id=version.id, status=DatasetStatus.ready, autocommit=False)
    await db.commit()

    # `Field.upsert_many` is a Core `INSERT ... RETURNING` (models/mixins.py) that does not
    # append to an already-loaded `dataset.fields` collection, and `expire_on_commit=False`
    # (database.py) means the commit above doesn't refresh it either. Without this refresh,
    # `create_index` -> `_configure_index_mappings` (search_engine/commons.py) iterates a
    # *stale* (or entirely unloaded, on a dataset fetched without those relationships
    # eager-loaded) collection: on an AsyncSession an unloaded lazy relationship raises
    # `MissingGreenlet`, and a stale-but-loaded one silently builds a `"dynamic": "strict"`
    # index missing properties for whatever it didn't see, so subsequent record writes touching
    # that gap are rejected at index time. `_configure_index_mappings` reads FOUR relationships
    # (search_engine/commons.py) -- all four must be refreshed, not just `fields`.
    await db.refresh(dataset, ["fields", "metadata_properties", "vectors_settings", "questions"])

    # Post-commit, outside the transaction -- the repo-wide convention for index side effects.
    #
    # `create_index` is NOT idempotent: both backends issue a bare `indices.create` that raises
    # `resource_already_exists_exception` on a second call for the same dataset, since
    # `es_index_name_for_dataset` is stable per dataset id. That makes every republish -- and
    # every schema-version publish on a dataset already published via `PUT /datasets/{id}/publish`
    # -- fail unconditionally. Guard with an explicit existence check (not a blanket-swallowed
    # 400, which would also hide a genuine mapping error on a real first create).
    if not await search_engine.index_exists(dataset):
        await search_engine.create_index(dataset)
    # else: the index already exists. Evolving its mapping for any newly-declared columns
    # (`put_mapping`) is explicitly out of scope for this fold -- see
    # docs/superpowers/plans/2026-07-26-fold-followups.md. A column added by this republish is
    # tracked as a `Field` row but is not yet queryable in the search index until that follow-up
    # lands (or LanceDB supersedes ES for this dataset shape entirely).

    if not was_already_ready:
        # Fire only on the draft -> ready transition, matching contexts/datasets.py::publish_dataset's
        # semantics (draft-gated by DatasetPublishValidator, so it can only ever fire once).
        # publish_version has no such gate -- it's legal to call repeatedly for version 2..n --
        # so without this guard every republish would re-fire `published` for an already-ready dataset.
        await notify_dataset_event_v1(db, DatasetEvent.published, dataset)

    return version


async def list_versions(db: AsyncSession, dataset: Dataset) -> list[SchemaVersion]:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset.id).order_by(SchemaVersion.version)
    return list((await db.execute(stmt)).scalars().all())


async def get_version_by_number(db: AsyncSession, dataset_id: UUID, version: int) -> SchemaVersion | None:
    stmt = select(SchemaVersion).where(SchemaVersion.dataset_id == dataset_id, SchemaVersion.version == version)
    return (await db.execute(stmt)).scalar_one_or_none()
