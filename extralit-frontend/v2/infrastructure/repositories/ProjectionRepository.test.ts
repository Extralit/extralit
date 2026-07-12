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
