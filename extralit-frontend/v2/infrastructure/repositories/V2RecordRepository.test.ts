import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { V2RecordRepository } from "./V2RecordRepository";
import { SearchCriteria } from "~/v2/domain/entities/search/SearchCriteria";

const BACKEND_RECORD = {
  id: "r-1",
  schema_id: "s-1",
  schema_version_id: "v-1",
  reference: "10.1000/j.x",
  external_id: null,
  fields: { title: "A study" },
  metadata: null,
  status: "pending",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("V2RecordRepository", () => {
  it("lists records with paging/reference params and maps the page", async () => {
    const axios = {
      get: vi.fn(async () => ({ data: { items: [BACKEND_RECORD], total: 12000 } })),
    } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    const page = await repository.getRecords("s-1", { offset: 0, limit: 25, reference: "10.1000/j.x" });

    expect((axios.get as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v2/schemas/s-1/records",
      { params: { offset: 0, limit: 25, reference: "10.1000/j.x" } },
    ]);
    expect(page.items[0].reference).toBe("10.1000/j.x");
    expect(page.total).toBe(12000);
  });

  it("posts search criteria to the :search custom verb", async () => {
    const axios = { post: vi.fn(async () => ({ data: { items: [], total: 0 } })) } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    await repository.searchRecords("s-1", new SearchCriteria("fts terms"));

    expect((axios.post as ReturnType<typeof vi.fn>).mock.calls[0]).toEqual([
      "/v2/schemas/s-1/records:search",
      { text: "fts terms", filters: [], offset: 0, limit: 50 },
    ]);
  });

  it("returns the indexed count from :rebuild-index", async () => {
    const axios = { post: vi.fn(async () => ({ data: { indexed: 42 } })) } as unknown as AxiosInstance;
    const repository = new V2RecordRepository(axios);

    await expect(repository.rebuildIndex("s-1")).resolves.toBe(42);
    expect(axios.post).toHaveBeenCalledWith("/v2/schemas/s-1:rebuild-index");
  });
});
