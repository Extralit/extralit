import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { SchemaRecordRepository } from "./SchemaRecordRepository";
import { SearchCriteria } from "~/v1/domain/entities/search/SearchCriteria";

const BACKEND_RECORD = {
  id: "r-1",
  dataset_id: "s-1",
  reference: "10.1000/j.x",
  external_id: null,
  fields: { title: "A study" },
  metadata: null,
  status: "pending",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("SchemaRecordRepository", () => {
  it("lists records with paging/reference params and maps the page", async () => {
    const axios = {
      get: vi.fn(async () => ({ data: { items: [BACKEND_RECORD], total: 12000 } })),
    } as unknown as AxiosInstance;
    const repository = new SchemaRecordRepository(axios);

    const page = await repository.getRecords("s-1", { offset: 0, limit: 25, reference: "10.1000/j.x" });

    expect((axios.get as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v1/datasets/s-1/records",
      { params: { offset: 0, limit: 25, reference: "10.1000/j.x", include: undefined } },
    ]);
    expect(page.items[0].reference).toBe("10.1000/j.x");
    expect(page.total).toBe(12000);
  });

  it("joins the include keys into a comma-separated query param", async () => {
    const axios = { get: vi.fn(async () => ({ data: { items: [], total: 0 } })) } as unknown as AxiosInstance;
    const repository = new SchemaRecordRepository(axios);

    await repository.getRecords("s-1", { include: ["responses", "suggestions"] });

    expect((axios.get as ReturnType<typeof vi.fn>).mock.calls[0][1]).toEqual({
      params: { offset: undefined, limit: undefined, reference: undefined, include: "responses,suggestions" },
    });
  });

  it("defaults a null total (server TODO: not-yet-required field) to 0", async () => {
    const axios = { get: vi.fn(async () => ({ data: { items: [], total: null } })) } as unknown as AxiosInstance;
    const repository = new SchemaRecordRepository(axios);

    const page = await repository.getRecords("s-1");

    expect(page.total).toBe(0);
  });

  it("posts search criteria to /records/search, offset/limit as query params, and returns the authoritative total", async () => {
    const axios = {
      post: vi.fn(async () => ({
        data: { items: [{ record: BACKEND_RECORD, query_score: 0.8 }], total: 1 },
      })),
    } as unknown as AxiosInstance;
    const repository = new SchemaRecordRepository(axios);

    const page = await repository.searchRecords("s-1", new SearchCriteria("fts terms", [], 10, 25));

    expect((axios.post as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v1/datasets/s-1/records/search",
      { query: { text: { q: "fts terms" } }, filters: null },
      { params: { offset: 10, limit: 25 } },
    ]);
    expect(page.items[0].reference).toBe("10.1000/j.x");
    expect(page.total).toBe(1);
  });

  it("translates an eq filter into a terms filter scoped to the record entity", async () => {
    const axios = { post: vi.fn(async () => ({ data: { items: [], total: 0 } })) } as unknown as AxiosInstance;
    const repository = new SchemaRecordRepository(axios);

    await repository.searchRecords("s-1", new SearchCriteria(null, [{ column: "status", op: "eq", value: "pending" }]));

    expect((axios.post as ReturnType<typeof vi.fn>).mock.calls[0][1]).toEqual({
      query: null,
      filters: { and: [{ type: "terms", scope: { entity: "record", property: "status" }, values: ["pending"] }] },
    });
  });
});
