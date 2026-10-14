import { describe, expect, it, vi } from "vitest";
import { ProjectionRepository } from "./ProjectionRepository";

// The server pins column order via `Dataset.name`, then `Question.inserted_at, Question.name`
// (contexts/v1/projection.py) — so ordering IS deterministic server-side, but it is definition
// order within a dataset, not alphabetical overall. This fixture is deliberately arranged
// non-alphabetically so an accidental client-side sort fails the order assertions below.
// It also covers the enriched-provenance fields end-to-end: a suggestion-sourced table
// sub-column with agent/score, and a list-valued score, which the contract permits.
const BACKEND_WORKSPACE = {
  columns: [
    {
      name: "Zeta.x",
      dataset_id: "s-2",
      dataset_name: "Zeta",
      question_name: "x",
      sub_column: null,
      dtype: "text",
    },
    {
      name: "Alpha.results.value",
      dataset_id: "s-1",
      dataset_name: "Alpha",
      question_name: "results",
      sub_column: "value",
      dtype: "table",
    },
    {
      name: "Alpha.labels",
      dataset_id: "s-1",
      dataset_name: "Alpha",
      question_name: "labels",
      sub_column: null,
      dtype: "multi_label_selection",
    },
  ],
  rows: [
    {
      reference: "10.1000/j.x",
      row_index: 0,
      cells: {
        "Zeta.x": { value: "RCT", source: "response", record_id: "r-1", agent: null, score: null },
        "Alpha.results.value": {
          value: "12%",
          source: "suggestion",
          record_id: "r-2",
          agent: "gpt-x",
          score: 0.92,
        },
        "Alpha.labels": {
          value: ["a", "b"],
          source: "suggestion",
          record_id: "r-2",
          agent: "gpt-x",
          score: [0.9, 0.1],
        },
      },
    },
  ],
  total_references: 213,
};

describe("ProjectionRepository", () => {
  describe("getWorkspaceProjection", () => {
    it("pages the workspace projection and maps snake_case to the domain shape, preserving server column/cell order", async () => {
      const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
      const page = await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1", 50, 25);

      expect(axios.get).toHaveBeenCalledWith("/v1/me/datasets/projection", {
        params: { workspace_id: "w-1", offset: 50, limit: 25 },
      });
      expect(page.totalReferences).toBe(213);

      // Ordering invariant: fails if columns are re-ordered/sorted anywhere in the mapping.
      expect(page.columns.map((c) => c.name)).toEqual(["Zeta.x", "Alpha.results.value", "Alpha.labels"]);
      expect(page.columns[0]).toEqual({
        name: "Zeta.x",
        datasetId: "s-2",
        datasetName: "Zeta",
        questionName: "x",
        subColumn: null,
        dtype: "text",
      });

      expect(page.rows[0].reference).toBe("10.1000/j.x");
      expect(page.rows[0].rowIndex).toBe(0);

      // Cell key order is incidental, not contractual — `toPerspectiveData` builds each row by
      // iterating `projection.columns`, never `row.cells` key order. Asserted only to document
      // that the mapping passes the server's object through rather than rebuilding it.
      expect(Object.keys(page.rows[0].cells)).toEqual(["Zeta.x", "Alpha.results.value", "Alpha.labels"]);
      expect(page.rows[0].cells["Zeta.x"]).toEqual({
        value: "RCT",
        source: "response",
        recordId: "r-1",
        agent: null,
        score: null,
      });

      // Enriched provenance: a transposition (agent<->score) or a dropped sub_column would
      // pass if every fixture cell null-filled these, so assert them populated.
      expect(page.columns[1].subColumn).toBe("value");
      expect(page.columns[1].dtype).toBe("table");
      expect(page.columns[2].subColumn).toBeNull();
      expect(page.rows[0].cells["Alpha.results.value"]).toEqual({
        value: "12%",
        source: "suggestion",
        recordId: "r-2",
        agent: "gpt-x",
        score: 0.92,
      });
      // The contract permits a list-valued score; it must survive unchanged.
      expect(page.rows[0].cells["Alpha.labels"]).toEqual({
        value: ["a", "b"],
        source: "suggestion",
        recordId: "r-2",
        agent: "gpt-x",
        score: [0.9, 0.1],
      });
    });

    it("defaults to offset 0, limit 50", async () => {
      const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
      await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1");
      expect(axios.get).toHaveBeenCalledWith("/v1/me/datasets/projection", {
        params: { workspace_id: "w-1", offset: 0, limit: 50 },
      });
    });
  });
});
