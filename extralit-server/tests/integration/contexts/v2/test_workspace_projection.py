import pytest

from extralit_server.contexts.v2 import projection as projection_ctx
from extralit_server.enums import QuestionType, ResponseStatus
from tests.factories import (
    SchemaFactory,
    SchemaVersionFactory,
    UserFactory,
    V2QuestionFactory,
    V2RecordFactory,
    V2ResponseFactory,
    V2SuggestionFactory,
    WorkspaceFactory,
)

pytestmark = pytest.mark.asyncio


async def _make_schema(workspace, name: str):
    schema = await SchemaFactory.create(workspace=workspace, name=name)
    version = await SchemaVersionFactory.create(schema=schema)
    return schema, version


async def _add_question(schema, name: str, *, qtype=QuestionType.text, columns=None):
    return await V2QuestionFactory.create(schema=schema, name=name, type=qtype, columns=columns or [name])


async def test_columns_manifest_covers_all_schemas_and_fans_out_table_bindings(db):
    workspace = await WorkspaceFactory.create()
    design, _ = await _make_schema(workspace, "Design")
    outcomes, _ = await _make_schema(workspace, "Outcomes")
    await _add_question(design, "type")
    await _add_question(outcomes, "results", qtype=QuestionType.table, columns=["value", "unit"])

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    names = [c.name for c in view.columns]
    assert names == ["Design.type", "Outcomes.results.value", "Outcomes.results.unit"]
    table_col = view.columns[1]
    assert table_col.schema_name == "Outcomes"
    assert table_col.question_name == "results"
    assert table_col.sub_column == "value"
    assert table_col.dtype == "table"


async def test_row_universe_is_union_of_references_with_coverage_gaps(db):
    workspace = await WorkspaceFactory.create()
    design, design_v = await _make_schema(workspace, "Design")
    outcomes, outcomes_v = await _make_schema(workspace, "Outcomes")
    dq = await _add_question(design, "type")
    await _add_question(outcomes, "summary")
    rec = await V2RecordFactory.create(version=design_v, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=dq, value="RCT")
    await V2RecordFactory.create(version=outcomes_v, reference="10.1/b")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert view.total_references == 2
    assert [(r.reference, r.row_index) for r in view.rows] == [("10.1/a", 0), ("10.1/b", 0)]
    row_a, row_b = view.rows
    assert row_a.cells["Design.type"].value == "RCT"
    assert "Outcomes.summary" not in row_a.cells  # no Outcomes record: coverage gap, cell omitted
    assert row_b.cells == {}  # record exists but neither response nor suggestion


async def test_latest_submitted_response_any_user_beats_suggestion(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user1 = await UserFactory.create()
    user2 = await UserFactory.create()
    await V2ResponseFactory.create(
        record=rec, user=user1, values={"type": {"value": "RCT-old"}}, status=ResponseStatus.submitted
    )
    await V2ResponseFactory.create(
        record=rec, user=user2, values={"type": {"value": "RCT"}}, status=ResponseStatus.submitted
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cell = view.rows[0].cells["Design.type"]
    assert cell.value == "RCT"  # later updated_at wins across users
    assert cell.source == "response"
    assert cell.record_id == rec.id
    assert cell.agent is None and cell.score is None


async def test_draft_responses_never_appear(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=q, value="cohort", agent="gpt-x", score=0.9)
    user = await UserFactory.create()
    await V2ResponseFactory.create(
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
    schema, version = await _make_schema(workspace, "Outcomes")
    scalar_q = await _add_question(schema, "design")
    t1 = await _add_question(schema, "results", qtype=QuestionType.table, columns=["value", "unit"])
    t2 = await _add_question(schema, "arms", qtype=QuestionType.table, columns=["arm"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=scalar_q, value="RCT")
    await V2SuggestionFactory.create(
        record=rec,
        question=t1,
        value=[{"value": "12%", "unit": "pct"}, {"value": "8%", "unit": "pct"}, {"value": "3%"}],
    )
    await V2SuggestionFactory.create(record=rec, question=t2, value=[{"arm": "control"}, {"arm": "treated"}])

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
    schema, version = await _make_schema(workspace, "Outcomes")
    t = await _add_question(schema, "results", qtype=QuestionType.table, columns=["value"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=rec, question=t, value={"value": "12%"})

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Outcomes.results.value"].value == "12%"


async def test_hostile_names_are_treated_as_ordinary_keys(db):
    """Question names and sub-column bindings are unconstrained user input. Interpolating them
    into a JSON path made a quote, a backslash or an empty name abort the WHOLE grid, and made a
    binding named `*` silently return every key's value."""
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Outcomes")
    await _add_question(schema, 'we"ird\\name')
    t = await _add_question(schema, "results", qtype=QuestionType.table, columns=['sub"col', "back\\slash", "", "*"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(
        record=rec,
        question=t,
        value=[{'sub"col': "A", "back\\slash": "B", "": "C", "*": "D", "unbound": "E"}],
    )
    user = await UserFactory.create()
    await V2ResponseFactory.create(
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
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    old = await V2RecordFactory.create(version=version, reference="10.1/a")
    new = await V2RecordFactory.create(version=version, reference="10.1/a")
    await V2SuggestionFactory.create(record=old, question=q, value="old")
    await V2SuggestionFactory.create(record=new, question=q, value="new")

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    assert len(view.rows) == 1
    assert view.rows[0].cells["Design.type"].value == "new"
    assert view.rows[0].cells["Design.type"].record_id == new.id


async def test_pagination_counts_references_not_rows(db):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    await _add_question(schema, "type")
    for i in range(5):
        await V2RecordFactory.create(version=version, reference=f"10.1/{i}")

    page = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=2, limit=2)

    assert page.total_references == 5
    assert [r.reference for r in page.rows] == ["10.1/2", "10.1/3"]  # ordered by reference


async def test_query_count_is_constant_regardless_of_reference_count(db, monkeypatch):
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    q = await _add_question(schema, "type")
    for i in range(6):
        rec = await V2RecordFactory.create(version=version, reference=f"10.1/{i}")
        await V2SuggestionFactory.create(record=rec, question=q, value=f"v{i}")

    executed: list[object] = []
    original_execute = db.execute

    async def counting_execute(*args, **kwargs):
        executed.append(args[0])
        return await original_execute(*args, **kwargs)

    monkeypatch.setattr(db, "execute", counting_execute)
    await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)
    # schemas, questions, ref-count, ref-page, records, suggestions, responses => 7 max
    assert len(executed) <= 7, f"N+1 regression: {len(executed)} statements"


async def test_multi_question_response_envelope_attributes_each_value_to_its_own_question(db):
    # The response path pairs json_keys(values_json) with json_extract(values_json, '$.*')
    # positionally and then joins on question_name. Every other test in this file submits a
    # single-key envelope, so a misalignment would be invisible. This is the real-world
    # shape: one user answering several questions on one record.
    workspace = await WorkspaceFactory.create()
    schema, version = await _make_schema(workspace, "Design")
    await _add_question(schema, "type")
    await _add_question(schema, "country")
    await _add_question(schema, "notes")
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    user = await UserFactory.create()
    await V2ResponseFactory.create(
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
    schema, version = await _make_schema(workspace, "Résumé")
    await _add_question(schema, "pays")
    table_q = await _add_question(schema, "résultats", qtype=QuestionType.table, columns=["café", "日本語"])
    rec = await V2RecordFactory.create(version=version, reference="10.1/a")
    user = await UserFactory.create()
    await V2SuggestionFactory.create(record=rec, question=table_q, value=[{"café": "noir", "日本語": "はい"}])
    await V2ResponseFactory.create(
        record=rec, user=user, status=ResponseStatus.submitted, values={"pays": {"value": "Côte d'Ivoire"}}
    )

    view = await projection_ctx.build_workspace_view(db, workspace_id=workspace.id, offset=0, limit=50)

    cells = view.rows[0].cells
    assert cells["Résumé.pays"].value == "Côte d'Ivoire"
    assert cells["Résumé.résultats.café"].value == "noir"
    assert cells["Résumé.résultats.日本語"].value == "はい"
