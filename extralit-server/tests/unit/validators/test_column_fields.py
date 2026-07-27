import pytest
from sqlalchemy.orm import selectinload

from extralit_server.api.schemas.v1.records import RecordCreate
from extralit_server.models import Dataset
from extralit_server.validators.records import RecordCreateValidator
from tests.database import TestSession
from tests.factories import DatasetFactory, FieldFactory


@pytest.mark.asyncio
class TestColumnFieldValidation:
    async def _dataset_with_column_fields(self):
        dataset = await DatasetFactory.create()
        await FieldFactory.create(
            dataset=dataset, name="population", settings={"type": "column", "dtype": "string", "nullable": True}
        )
        await FieldFactory.create(
            dataset=dataset, name="n_arms", settings={"type": "column", "dtype": "int64", "nullable": True}
        )

        # `DatasetFactory.refresh_with_relationships` does not exist; reload with the
        # same four `selectinload`s used at api/handlers/v1/datasets/records_bulk.py:36-42.
        return await Dataset.get_or_raise(
            TestSession(),
            dataset.id,
            options=[
                selectinload(Dataset.fields),
                selectinload(Dataset.questions),
                selectinload(Dataset.metadata_properties),
                selectinload(Dataset.vectors_settings),
            ],
        )

    async def test_column_fields_accept_any_json_scalar(self):
        dataset = await self._dataset_with_column_fields()
        # A bare int/float/bool can never reach this validator at all: `RecordCreate.fields`
        # values are a schema-level union of `str | list[ChatFieldValue] | dict | None`
        # (`api/schemas/v1/records.py::FieldValueCreate`), applied identically regardless of
        # field type, before any per-field-type dispatch. That boundary is independently
        # pinned by test_create_dataset_records_bulk_with_wrong_text_field_value (values 1,
        # 1.0, True all 422 there) — changing it is out of scope for this task and would
        # break that lock-down. What we *can* prove here is the actual claim under test: a
        # value a text field's collector would reject outright (`_validate_text_field`
        # requires `isinstance(value, str)`) must NOT be rejected the way a text field would
        # be, because no collector selects a column field.
        await RecordCreateValidator.validate(
            RecordCreate(fields={"population": "Kenya", "n_arms": {"raw": 2}}), dataset
        )

    async def test_column_fields_accept_null(self):
        dataset = await self._dataset_with_column_fields()
        await RecordCreateValidator.validate(RecordCreate(fields={"population": None, "n_arms": None}), dataset)

    async def test_column_fields_accept_nested_json(self):
        dataset = await self._dataset_with_column_fields()
        # See the note above: `[1, 2]` cannot reach this validator (`FieldValueCreate` has no
        # bare `list[int]` member and the `list[ChatFieldValue]` before-validator rejects
        # non-dict list items with a hard error). A dict and a chat-shaped list are both
        # legal `FieldValueCreate` shapes that a text field's collector would still reject.
        await RecordCreateValidator.validate(
            RecordCreate(fields={"population": {"country": "Kenya"}, "n_arms": [{"role": "user", "content": "2"}]}),
            dataset,
        )

    async def test_undeclared_columns_are_still_rejected(self):
        dataset = await self._dataset_with_column_fields()
        with pytest.raises(Exception) as excinfo:
            await RecordCreateValidator.validate(RecordCreate(fields={"not_a_column": "x"}), dataset)
        assert "not_a_column" in str(excinfo.value)
