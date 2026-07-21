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
});

const BACKEND_WORKSPACE = {
  columns: [
    {
      name: "Design.type",
      schema_id: "s-1",
      schema_name: "Design",
      question_name: "type",
      sub_column: null,
      dtype: "text",
    },
  ],
  rows: [
    {
      reference: "10.1000/j.x",
      row_index: 0,
      cells: {
        "Design.type": { value: "RCT", source: "response", record_id: "r-1", agent: null, score: null },
      },
    },
  ],
  total_references: 213,
};

describe("getWorkspaceProjection", () => {
  it("pages the workspace projection and maps snake_case to the domain shape", async () => {
    const axios = { get: vi.fn(async () => ({ data: BACKEND_WORKSPACE })) };
    const page = await new ProjectionRepository(axios as never).getWorkspaceProjection("w-1", 50, 25);

    expect(axios.get).toHaveBeenCalledWith("/v2/projection", {
      params: { workspace_id: "w-1", offset: 50, limit: 25 },
    });
    expect(page.totalReferences).toBe(213);
    expect(page.columns[0]).toEqual({
      name: "Design.type",
      schemaId: "s-1",
      schemaName: "Design",
      questionName: "type",
      subColumn: null,
      dtype: "text",
    });
    expect(page.rows[0].reference).toBe("10.1000/j.x");
    expect(page.rows[0].rowIndex).toBe(0);
    expect(page.rows[0].cells["Design.type"]).toEqual({
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
