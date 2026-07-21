import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { ProjectionRepository } from "./ProjectionRepository";

const BACKEND_VIEW = {
  reference: "10.1000/j.x",
  total_records: 1,
  records: [
    {
      record_id: "r-1",
      schema_id: "s-1",
      reference: "10.1000/j.x",
      cells: [
        { question_name: "size", value: "12", source: "suggestion" },
        { question_name: "note", value: null, source: null },
      ],
    },
  ],
};

// Columns deliberately out of alphabetical order — the server orders columns by schema/question
// definition order, not alphabetically, and nothing on the server pins that order. The grid's
// column layout depends on it, so the mapping must preserve exactly what the server sent.
const BACKEND_WORKSPACE = {
  columns: [
    {
      name: "Zeta.x",
      schema_id: "s-2",
      schema_name: "Zeta",
      question_name: "x",
      sub_column: null,
      dtype: "text",
    },
    {
      name: "Alpha.y",
      schema_id: "s-1",
      schema_name: "Alpha",
      question_name: "y",
      sub_column: null,
      dtype: "text",
    },
  ],
  rows: [
    {
      reference: "10.1000/j.x",
      row_index: 0,
      cells: {
        "Zeta.x": { value: "RCT", source: "response", record_id: "r-1", agent: null, score: null },
        "Alpha.y": { value: "42", source: "response", record_id: "r-2", agent: null, score: null },
      },
    },
  ],
  total_references: 213,
};

describe("ProjectionRepository", () => {
  it("percent-encodes the slashed reference and maps the view to DTOs (seam B)", async () => {
    const axios = { get: vi.fn(async () => ({ data: BACKEND_VIEW })) } as unknown as AxiosInstance;

    const view = await new ProjectionRepository(axios).getProjection("10.1000/j.x", "w-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/projection/references/10.1000%2Fj.x", {
      params: { workspace_id: "w-1" },
    });
    expect(view).toEqual({
      reference: "10.1000/j.x",
      totalRecords: 1,
      records: [
        {
          recordId: "r-1",
          schemaId: "s-1",
          reference: "10.1000/j.x",
          cells: [
            { questionName: "size", value: "12", source: "suggestion" },
            { questionName: "note", value: null, source: null },
          ],
        },
      ],
    });
  });

  describe("getWorkspaceProjection", () => {
    it("pages the workspace projection and maps snake_case to the domain shape, preserving server column/cell order", async () => {
      const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
      const page = await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1", 50, 25);

      expect(axios.get).toHaveBeenCalledWith("/v2/projection", {
        params: { workspace_id: "w-1", offset: 50, limit: 25 },
      });
      expect(page.totalReferences).toBe(213);

      // Ordering invariant: fails if columns are re-ordered/sorted anywhere in the mapping.
      expect(page.columns.map((c) => c.name)).toEqual(["Zeta.x", "Alpha.y"]);
      expect(page.columns[0]).toEqual({
        name: "Zeta.x",
        schemaId: "s-2",
        schemaName: "Zeta",
        questionName: "x",
        subColumn: null,
        dtype: "text",
      });

      expect(page.rows[0].reference).toBe("10.1000/j.x");
      expect(page.rows[0].rowIndex).toBe(0);

      // Ordering invariant: fails if cells are rebuilt via a Map/sort that loses server key order.
      expect(Object.keys(page.rows[0].cells)).toEqual(["Zeta.x", "Alpha.y"]);
      expect(page.rows[0].cells["Zeta.x"]).toEqual({
        value: "RCT",
        source: "response",
        recordId: "r-1",
        agent: null,
        score: null,
      });
    });

    it("defaults to offset 0, limit 50", async () => {
      const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
      await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1");
      expect(axios.get).toHaveBeenCalledWith("/v2/projection", {
        params: { workspace_id: "w-1", offset: 0, limit: 50 },
      });
    });
  });
});
