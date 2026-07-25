import { describe, expect, it } from "vitest";
import { bandParity, REFERENCE_COLUMN, toPerspectiveData } from "./grid-adapter";
import { WorkspaceProjection, type ProjectionGridCell } from "./WorkspaceProjection";

const cell = (value: unknown): ProjectionGridCell => ({
  value,
  source: "suggestion",
  recordId: "r-1",
  agent: "gpt-x",
  score: 0.9,
});

const COLUMNS = [
  { name: "Design.type", schemaId: "s-1", schemaName: "Design", questionName: "type", subColumn: null, dtype: "text" },
  {
    name: "Outcomes.results.value",
    schemaId: "s-2",
    schemaName: "Outcomes",
    questionName: "results",
    subColumn: "value",
    dtype: "table",
  },
];

const PROJECTION = new WorkspaceProjection(
  COLUMNS,
  [
    { reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell("RCT") } },
    { reference: "10.1/a", rowIndex: 1, cells: { "Outcomes.results.value": cell("12%") } },
    { reference: "10.1/b", rowIndex: 0, cells: {} },
  ],
  2
);

describe("toPerspectiveData", () => {
  it("emits one flat record per row with every manifest column (null when absent)", () => {
    expect(toPerspectiveData(PROJECTION)).toEqual([
      { [REFERENCE_COLUMN]: "10.1/a", "Design.type": "RCT", "Outcomes.results.value": null },
      { [REFERENCE_COLUMN]: "10.1/a", "Design.type": null, "Outcomes.results.value": "12%" },
      { [REFERENCE_COLUMN]: "10.1/b", "Design.type": null, "Outcomes.results.value": null },
    ]);
  });

  it("preserves manifest column order (not alphabetical), reference first", () => {
    // Deliberately reverse-alphabetical ("Zebra" before "Apple") so this test fails if
    // anyone re-sorts columns instead of following `projection.columns` order.
    const orderColumns = [
      {
        name: "Zebra.value",
        schemaId: "s-2",
        schemaName: "Zebra",
        questionName: "value",
        subColumn: null,
        dtype: "text",
      },
      {
        name: "Apple.value",
        schemaId: "s-1",
        schemaName: "Apple",
        questionName: "value",
        subColumn: null,
        dtype: "text",
      },
    ];
    const orderProjection = new WorkspaceProjection(orderColumns, [{ reference: "10.1/a", rowIndex: 0, cells: {} }], 1);
    const rows = toPerspectiveData(orderProjection);
    expect(Object.keys(rows[0])).toEqual([REFERENCE_COLUMN, "Zebra.value", "Apple.value"]);
  });

  it("excludes cell keys that are not present in the column manifest", () => {
    const extraCellProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Unlisted.column": cell("x") } }],
      1
    );
    expect(toPerspectiveData(extraCellProjection)).toEqual([
      { [REFERENCE_COLUMN]: "10.1/a", "Design.type": null, "Outcomes.results.value": null },
    ]);
  });

  it("returns an empty array for a projection with no rows", () => {
    const empty = new WorkspaceProjection(COLUMNS, [], 0);
    expect(toPerspectiveData(empty)).toEqual([]);
  });

  it("serializes an array cell value to a stable JSON string (multi_label_selection / ranking)", () => {
    const arrayProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell(["low", "high"]) } }],
      1
    );
    expect(toPerspectiveData(arrayProjection)[0]["Design.type"]).toBe(JSON.stringify(["low", "high"]));
  });

  it("serializes an object cell value to a stable JSON string (span)", () => {
    const spanProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell({ start: 0, end: 3, text: "RCT" }) } }],
      1
    );
    expect(toPerspectiveData(spanProjection)[0]["Design.type"]).toBe(JSON.stringify({ start: 0, end: 3, text: "RCT" }));
  });

  it('keeps an absent cell as the JS value null, not the string "null"', () => {
    expect(toPerspectiveData(PROJECTION)[2]["Design.type"]).toBeNull();
  });

  it('keeps a cell whose value is explicitly null as null, not the string "null"', () => {
    const explicitNullProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell(null) } }],
      1
    );
    expect(toPerspectiveData(explicitNullProjection)[0]["Design.type"]).toBeNull();
  });

  it("returns null instead of throwing for a circular-object cell value", () => {
    // JSON.stringify throws on a circular structure; toScalarCell must coerce that to `null`
    // (per its own contract) rather than let it escape as an unhandled exception that would
    // surface as a spurious `load-error` out of `performLoad`.
    const circular: Record<string, unknown> = { a: 1 };
    circular.self = circular;
    const circularProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell(circular) } }],
      1
    );
    expect(toPerspectiveData(circularProjection)[0]["Design.type"]).toBeNull();
  });

  it("returns null, not undefined, for a function cell value (JSON.stringify itself returns undefined)", () => {
    // JSON.stringify(fn) === undefined, not a string — without the `?? null` coercion this
    // key would be `undefined`, breaking the "every manifest column present, null when
    // absent" contract that downstream schema inference depends on.
    const fnProjection = new WorkspaceProjection(
      COLUMNS,
      [{ reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell(() => "x") } }],
      1
    );
    expect(toPerspectiveData(fnProjection)[0]["Design.type"]).toBeNull();
  });

  it("passes scalar cell values (string, number, boolean) through unchanged", () => {
    const scalarProjection = new WorkspaceProjection(
      COLUMNS,
      [
        { reference: "10.1/a", rowIndex: 0, cells: { "Design.type": cell("RCT") } },
        { reference: "10.1/b", rowIndex: 0, cells: { "Design.type": cell(42) } },
        { reference: "10.1/c", rowIndex: 0, cells: { "Design.type": cell(true) } },
      ],
      1
    );
    const rows = toPerspectiveData(scalarProjection);
    expect(rows[0]["Design.type"]).toBe("RCT");
    expect(rows[1]["Design.type"]).toBe(42);
    expect(rows[2]["Design.type"]).toBe(true);
  });
});

describe("bandParity", () => {
  it("flips parity when the reference changes, not per row", () => {
    expect(bandParity(PROJECTION)).toEqual([0, 0, 1]);
  });

  it("does not merge a reference that recurs after a gap", () => {
    const gapped = new WorkspaceProjection(
      COLUMNS,
      [
        { reference: "10.1/a", rowIndex: 0, cells: {} },
        { reference: "10.1/b", rowIndex: 0, cells: {} },
        { reference: "10.1/a", rowIndex: 0, cells: {} },
      ],
      2
    );
    expect(bandParity(gapped)).toEqual([0, 1, 0]);
  });

  it("returns an empty array for a projection with no rows", () => {
    const empty = new WorkspaceProjection(COLUMNS, [], 0);
    expect(bandParity(empty)).toEqual([]);
  });
});
