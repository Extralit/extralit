import { describe, expect, it } from "vitest";
import {
  ANNOTATION_CELL_LINKS_ENABLED,
  bandParity,
  buildAnnotationUrl,
  cellAt,
  REFERENCE_COLUMN,
  toPerspectiveData,
} from "./grid-adapter";
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
});

describe("cellAt", () => {
  it("returns the enriched cell for the loaded row order", () => {
    expect(cellAt(PROJECTION, 0, "Design.type")?.recordId).toBe("r-1");
  });

  it("returns null for empty cells and out-of-range rows", () => {
    expect(cellAt(PROJECTION, 2, "Design.type")).toBeNull();
    expect(cellAt(PROJECTION, 99, "Design.type")).toBeNull();
  });
});

describe("bandParity", () => {
  it("flips parity when the reference changes, not per row", () => {
    expect(bandParity(PROJECTION)).toEqual([0, 0, 1]);
  });
});

describe("annotation URL contract (spec §3.3)", () => {
  it("stays guarded off in this build", () => {
    expect(ANNOTATION_CELL_LINKS_ENABLED).toBe(false);
  });

  it("puts the schema id in the dataset slot and encodes the reference", () => {
    expect(buildAnnotationUrl("s-1", "10.1/a b")).toBe("/dataset/s-1/annotation-mode?_search=10.1%2Fa%20b");
  });
});
