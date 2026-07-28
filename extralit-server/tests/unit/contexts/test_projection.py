from datetime import datetime
from uuid import UUID

import pytest

from extralit_server.contexts import projection as projection_ctx
from extralit_server.enums import QuestionType, ResponseStatus
from extralit_server.models.database import Dataset
from tests.factories import (
    ColumnFieldFactory,
    DatasetFactory,
    QuestionFactory,
    RecordFactory,
    ResponseFactory,
    SchemaVersionFactory,
    SuggestionFactory,
    UserFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.asyncio


async def schema_backed_dataset(workspace, *, name: str) -> Dataset:
    """A dataset with a published schema version and one declared column: the
    discriminator (`Dataset.current_schema_version_id IS NOT NULL`) that makes a dataset
    an extraction project eligible for the workspace projection."""
    dataset = await DatasetFactory.create(workspace=workspace, name=name)
    version = await SchemaVersionFactory.create(dataset=dataset)
    await dataset.update(dataset.current_async_session, current_schema_version_id=version.id)
    await ColumnFieldFactory.create(dataset=dataset, name="col")
    return dataset


async def _add_question(dataset, name: str, *, qtype=QuestionType.text, columns=None):
    return await QuestionFactory.create(
        dataset=dataset, name=name, settings={"type": qtype.value, "columns": columns or [name]}
    )


async def test_columns_manifest_covers_all_schemas_and_fans_out_table_bindings(db):
    workspace = await WorkspaceFactory.create()
    design = await schema_backed_dataset(workspace, name="Design")
    outcomes = await schema_backed_dataset(workspace, name="Outcomes")
    await _add_question(design, "type")
    await _add_question(outcomes, "results", qtype=QuestionType.table, columns=["value", "unit"])

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    names = [c.name for c in view.columns]
    assert names == ["Design.type", "Outcomes.results.value", "Outcomes.results.unit"]
    table_col = view.columns[1]
    assert table_col.dataset_name == "Outcomes"
    assert table_col.question_name == "results"
    assert table_col.sub_column == "value"
    assert table_col.dtype == "table"


async def test_row_universe_is_union_of_references_with_coverage_gaps(db):
    workspace = await WorkspaceFactory.create()
    design = await schema_backed_dataset(workspace, name="Design")
    outcomes = await schema_backed_dataset(workspace, name="Outcomes")
    dq = await _add_question(design, "type")
    await _add_question(outcomes, "summary")
    rec = await RecordFactory.create(dataset=design, reference="10.1/a")
    await SuggestionFactory.create(record=rec, question=dq, value="RCT")
    await RecordFactory.create(dataset=outcomes, reference="10.1/b")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.total_references == 2
    assert [(r.reference, r.row_index) for r in view.rows] == [("10.1/a", 0), ("10.1/b", 0)]
    row_a, row_b = view.rows
    assert row_a.cells["Design.type"].value == "RCT"
    assert "Outcomes.summary" not in row_a.cells  # no Outcomes record: coverage gap, cell omitted
    assert row_b.cells == {}  # record exists but neither response nor suggestion


async def test_latest_submitted_response_any_user_beats_suggestion(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    q = await _add_question(dataset, "type")
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user1 = await UserFactory.create()
    user2 = await UserFactory.create()
    # Explicit, distinct timestamps: left to the TimestampMixin default (`datetime.utcnow`) these
    # two land on the same instant, and the winner would fall through to the `response_id DESC`
    # tiebreaker -- deterministic, but decided by a UUID rather than by the rule this test names.
    await ResponseFactory.create(
        record=rec,
        user=user1,
        values={"type": {"value": "RCT-old"}},
        status=ResponseStatus.submitted,
        updated_at=datetime(2026, 7, 20, 12, 0, 0),
    )
    await ResponseFactory.create(
        record=rec,
        user=user2,
        values={"type": {"value": "RCT"}},
        status=ResponseStatus.submitted,
        updated_at=datetime(2026, 7, 20, 12, 5, 0),
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cell = view.rows[0].cells["Design.type"]
    assert cell.value == "RCT"  # later updated_at wins across users
    assert cell.source == "response"
    assert cell.record_id == rec.id
    assert cell.agent is None and cell.score is None


async def test_draft_responses_never_appear(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    q = await _add_question(dataset, "type")
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user = await UserFactory.create()
    await ResponseFactory.create(
        record=rec, user=user, values={"type": {"value": "draft-val"}}, status=ResponseStatus.draft
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cell = view.rows[0].cells["Design.type"]
    assert cell.value == "cohort"
    assert cell.source == "suggestion"
    assert cell.agent == "gpt-x"
    assert cell.score == 0.9


async def test_table_fanout_independent_stacking_and_scalar_repetition(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Outcomes")
    scalar_q = await _add_question(dataset, "design")
    t1 = await _add_question(dataset, "results", qtype=QuestionType.table, columns=["value", "unit"])
    t2 = await _add_question(dataset, "arms", qtype=QuestionType.table, columns=["arm"])
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(record=rec, question=scalar_q, value="RCT")
    await SuggestionFactory.create(
        record=rec,
        question=t1,
        value=[{"value": "12%", "unit": "pct"}, {"value": "8%", "unit": "pct"}, {"value": "3%"}],
    )
    await SuggestionFactory.create(record=rec, question=t2, value=[{"arm": "control"}, {"arm": "treated"}])

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.total_references == 1
    assert len(view.rows) == 3  # max(3, 2), NOT 3*2 (no cartesian product)
    assert [r.row_index for r in view.rows] == [0, 1, 2]
    # scalars repeat on every fan-out row (true denormalized rows)
    assert all(r.cells["Outcomes.design"].value == "RCT" for r in view.rows)
    assert [r.cells["Outcomes.results.value"].value for r in view.rows] == ["12%", "8%", "3%"]
    # shorter table just ends (independent stacking): row 2 has no arms cell
    assert [r.cells.get("Outcomes.arms.arm") and r.cells["Outcomes.arms.arm"].value for r in view.rows] == [
        "control",
        "treated",
        None,
    ]
    # missing sub-key on a row dict is omitted
    assert "Outcomes.results.unit" not in view.rows[2].cells


async def test_single_dict_table_value_is_one_row(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Outcomes")
    t = await _add_question(dataset, "results", qtype=QuestionType.table, columns=["value"])
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(record=rec, question=t, value={"value": "12%"})

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Outcomes.results.value"].value == "12%"


async def test_hostile_names_are_treated_as_ordinary_keys(db):
    """Question names and sub-column bindings are unconstrained user input. Interpolating them
    into a JSON path made a quote, a backslash or an empty name abort the WHOLE grid, and made a
    binding named `*` silently return every key's value."""
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Outcomes")
    await _add_question(dataset, 'we"ird\\name')
    t = await _add_question(dataset, "results", qtype=QuestionType.table, columns=['sub"col', "back\\slash", "", "*"])
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(
        record=rec,
        question=t,
        value=[{'sub"col': "A", "back\\slash": "B", "": "C", "*": "D", "unbound": "E"}],
    )
    user = await UserFactory.create()
    await ResponseFactory.create(
        record=rec, user=user, values={'we"ird\\name': {"value": "RCT"}}, status=ResponseStatus.submitted
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert [c.name for c in view.columns] == [
        'Outcomes.we"ird\\name',
        'Outcomes.results.sub"col',
        "Outcomes.results.back\\slash",
        "Outcomes.results.",
        "Outcomes.results.*",
    ]
    cells = view.rows[0].cells
    assert cells['Outcomes.we"ird\\name'].value == "RCT"
    assert cells['Outcomes.we"ird\\name'].source == "response"
    assert cells['Outcomes.results.sub"col'].value == "A"
    assert cells["Outcomes.results.back\\slash"].value == "B"
    assert cells["Outcomes.results."].value == "C"
    assert cells["Outcomes.results.*"].value == "D"  # a literal key, not a wildcard
    assert "Outcomes.results.unbound" not in cells


async def test_effective_record_is_latest_inserted_per_reference_schema(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    q = await _add_question(dataset, "type")
    old = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    new = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await SuggestionFactory.create(record=old, question=q, value="old")
    await SuggestionFactory.create(record=new, question=q, value="new")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Design.type"].value == "new"
    assert view.rows[0].cells["Design.type"].record_id == new.id


async def test_pagination_counts_references_not_rows(db):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    await _add_question(dataset, "type")
    for i in range(5):
        await RecordFactory.create(dataset=dataset, reference=f"10.1/{i}")

    page = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=2, limit=2)

    assert page.total_references == 5
    assert [r.reference for r in page.rows] == ["10.1/2", "10.1/3"]  # ordered by reference


async def test_null_reference_records_do_not_burn_a_page_slot(db):
    # v1's `Record.reference` is nullable (v2's `V2Record.reference` was NOT NULL). A record
    # with no reference must be excluded from both the reference count and the paged reference
    # list -- otherwise `group_by(Record.reference)` forms a NULL group that occupies a page
    # slot but `Record.reference.in_([..., None])` never matches it, silently returning fewer
    # rows than `limit` on some page.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    await _add_question(dataset, "type")
    for i in range(3):
        await RecordFactory.create(dataset=dataset, reference=f"10.1/{i}")
    await RecordFactory.create(dataset=dataset, reference=None)

    first_page = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=2)
    assert first_page.total_references == 3
    assert [r.reference for r in first_page.rows] == ["10.1/0", "10.1/1"]

    second_page = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=2, limit=2)
    assert [r.reference for r in second_page.rows] == ["10.1/2"]


async def test_query_count_is_constant_regardless_of_reference_count(db, monkeypatch):
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    q = await _add_question(dataset, "type")
    for i in range(6):
        rec = await RecordFactory.create(dataset=dataset, reference=f"10.1/{i}")
        await SuggestionFactory.create(record=rec, question=q, value=f"v{i}")

    executed: list[object] = []
    original_execute = db.execute

    async def counting_execute(*args, **kwargs):
        executed.append(args[0])
        return await original_execute(*args, **kwargs)

    monkeypatch.setattr(db, "execute", counting_execute)
    await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)
    # datasets, questions, ref-count, ref-page, records, suggestions, responses => 7 max
    assert len(executed) <= 7, f"N+1 regression: {len(executed)} statements"


async def test_multi_question_response_envelope_attributes_each_value_to_its_own_question(db):
    # The response path pairs json_keys(values_json) with json_extract(values_json, '$.*')
    # positionally and then joins on question_name. Every other test in this file submits a
    # single-key envelope, so a misalignment would be invisible. This is the real-world
    # shape: one user answering several questions on one record.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    await _add_question(dataset, "type")
    await _add_question(dataset, "country")
    await _add_question(dataset, "notes")
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    user = await UserFactory.create()
    await ResponseFactory.create(
        record=rec,
        user=user,
        status=ResponseStatus.submitted,
        values={
            "type": {"value": "RCT"},
            "country": {"value": "KE"},
            "notes": {"value": "multi-site"},
        },
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cells = view.rows[0].cells
    assert cells["Design.type"].value == "RCT"
    assert cells["Design.country"].value == "KE"
    assert cells["Design.notes"].value == "multi-site"
    assert all(cells[name].source == "response" for name in ("Design.type", "Design.country", "Design.notes"))


async def test_non_ascii_names_and_bindings_resolve(db):
    # Both joins compare Python strings against keys DuckDB parsed out of JSON text.
    # Non-ASCII names must survive that round-trip (see ensure_ascii=False at the input
    # serialization) — a mismatch would silently omit the cell rather than error.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Résumé")
    # `país` is non-ASCII so it exercises the response-envelope join (rc.question_name =
    # q.question_name) against a key DuckDB parsed from values_json — the half of the
    # ensure_ascii=False change on the responses serialization that an ASCII name would miss.
    await _add_question(dataset, "país")
    table_q = await _add_question(dataset, "résultats", qtype=QuestionType.table, columns=["café", "日本語"])
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    user = await UserFactory.create()
    await SuggestionFactory.create(record=rec, question=table_q, value=[{"café": "noir", "日本語": "はい"}])
    await ResponseFactory.create(
        record=rec, user=user, status=ResponseStatus.submitted, values={"país": {"value": "Côte d'Ivoire"}}
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cells = view.rows[0].cells
    assert cells["Résumé.país"].value == "Côte d'Ivoire"
    assert cells["Résumé.résultats.café"].value == "noir"
    assert cells["Résumé.résultats.日本語"].value == "はい"


async def test_table_fanout_through_the_response_path(db):
    # Every other fan-out test seeds a *suggestion*, whose value_json is the row array directly.
    # A response arrives double-wrapped instead -- {question_name: {"value": [...]}} -- so the
    # rows only reach `table_arrays` if `json_extract(entry, '$.value')` unwraps the envelope
    # first. Nothing else in this file exercises that seam.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Outcomes")
    await _add_question(dataset, "results", qtype=QuestionType.table, columns=["value", "unit"])
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    user = await UserFactory.create()
    await ResponseFactory.create(
        record=rec,
        user=user,
        status=ResponseStatus.submitted,
        values={"results": {"value": [{"value": "12%", "unit": "pct"}, {"value": "8%", "unit": "pct"}]}},
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 2  # fan-out happens on the response path too, not just suggestions
    assert [r.cells["Outcomes.results.value"].value for r in view.rows] == ["12%", "8%"]
    assert all(r.cells["Outcomes.results.value"].source == "response" for r in view.rows)
    assert all(r.cells["Outcomes.results.unit"].value == "pct" for r in view.rows)


# Explicit ids so both sort keys of `latest_responses` are controlled: the tiebreaker compares
# them as VARCHAR (that is how they are loaded into DuckDB), and "...0b" > "...0a".
_LOWER_ID = UUID("00000000-0000-0000-0000-0000000000aa")
_HIGHER_ID = UUID("00000000-0000-0000-0000-0000000000bb")


async def _two_responses(record, *, lower_at: datetime, higher_at: datetime):
    """Two submitted responses on one record with pinned ids and timestamps."""
    for response_id, value, updated_at in (
        (_LOWER_ID, "lower-id", lower_at),
        (_HIGHER_ID, "higher-id", higher_at),
    ):
        await ResponseFactory.create(
            id=response_id,
            record=record,
            user=await UserFactory.create(),
            status=ResponseStatus.submitted,
            values={"type": {"value": value}},
            updated_at=updated_at,
        )


async def test_tied_response_timestamps_resolve_deterministically(db):
    # `updated_at` defaults to `datetime.utcnow`, so two users submitting back-to-back can share
    # a timestamp exactly. Without the `response_id DESC` tiebreaker in `latest_responses` the
    # winning envelope is whatever order Postgres happened to return -- a coin flip in prod and a
    # flaky test here. Pin both timestamps to the same instant so the tiebreaker is the *only*
    # thing deciding, then assert the documented rule: greatest id wins.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    await _add_question(dataset, "type")
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    tied_at = datetime(2026, 7, 20, 12, 0, 0)
    await _two_responses(rec, lower_at=tied_at, higher_at=tied_at)

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.rows[0].cells["Design.type"].value == "higher-id"


async def test_updated_at_dominates_the_response_id_tiebreaker(db):
    # Pins the two keys' *precedence*, which the tie test above cannot: there, both orderings
    # agree. Here the lower id carries the later timestamp, so `updated_at DESC, response_id DESC`
    # and a bare `response_id DESC` disagree -- dropping or demoting `updated_at` fails this test.
    workspace = await WorkspaceFactory.create()
    dataset = await schema_backed_dataset(workspace, name="Design")
    await _add_question(dataset, "type")
    rec = await RecordFactory.create(dataset=dataset, reference="10.1/a")
    await _two_responses(
        rec,
        lower_at=datetime(2026, 7, 20, 12, 5, 0),  # later, on the *lower* id
        higher_at=datetime(2026, 7, 20, 12, 0, 0),
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.rows[0].cells["Design.type"].value == "lower-id"


async def test_only_schema_backed_datasets_appear_in_the_projection(db):
    """A plain annotation dataset in the same workspace must not leak into the grid."""
    workspace = await WorkspaceFactory.create()
    plain = await DatasetFactory.create(workspace=workspace)
    await QuestionFactory.create(dataset=plain, name="sentiment")
    await RecordFactory.create(dataset=plain, reference="ref-1")

    projection = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=10)
    assert projection.columns == []
    assert projection.rows == []
    assert projection.total_references == 0


async def test_datasets_are_ordered_by_name(db):
    workspace = await WorkspaceFactory.create()
    for name in ("zeta", "alpha"):
        dataset = await schema_backed_dataset(workspace, name=name)
        await QuestionFactory.create(dataset=dataset, name="q", settings={"type": "text", "columns": ["c"]})
    projection = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=10)
    assert [c.dataset_name for c in projection.columns] == ["alpha", "zeta"]
