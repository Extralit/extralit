import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { SchemaRepository } from "./SchemaRepository";

const axiosMock = (getImpl: (url: string) => unknown) =>
  ({ get: vi.fn(async (url: string) => ({ data: getImpl(url) })) }) as unknown as AxiosInstance;

const BACKEND_SCHEMA = {
  id: "s-1",
  name: "sample_size",
  status: "published",
  current_version_id: "v-1",
  settings: {},
  workspace_id: "w-1",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("SchemaRepository", () => {
  it("lists schemas for a workspace and maps to domain entities", async () => {
    const axios = axiosMock(() => ({ items: [BACKEND_SCHEMA] }));
    const repository = new SchemaRepository(axios);

    const schemas = await repository.getSchemas("w-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/schemas", { params: { workspace_id: "w-1" } });
    expect(schemas[0].workspaceId).toBe("w-1");
    expect(schemas[0].currentVersionId).toBe("v-1");
  });

  it("fetches a single schema and maps it to a domain entity", async () => {
    const axios = axiosMock(() => BACKEND_SCHEMA);
    const repository = new SchemaRepository(axios);

    const schema = await repository.getSchema("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/schemas/s-1");
    expect(schema.id).toBe("s-1");
    expect(schema.name).toBe("sample_size");
    expect(schema.currentVersionId).toBe("v-1");
  });

  it("maps versions including columns_cache to ColumnMeta", async () => {
    const axios = axiosMock(() => [
      {
        id: "v-1",
        schema_id: "s-1",
        version: 1,
        object_key: "k",
        object_version_id: null,
        etag: "e",
        checksum: "c",
        parent_version_id: null,
        columns_cache: [{ name: "title", dtype: "str", nullable: false, review: { type: "text" } }],
        review_widgets: {},
        inserted_at: "2026-01-01T00:00:00",
      },
    ]);
    const repository = new SchemaRepository(axios);

    const versions = await repository.getVersions("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v2/schemas/s-1/versions");
    expect(versions[0].findColumn("title")?.review?.type).toBe("text");
  });

  it("maps questions preserving type, columns and settings", async () => {
    const axios = axiosMock(() => ({
      items: [
        {
          id: "q-1",
          schema_id: "s-1",
          name: "label",
          title: "Label",
          description: null,
          type: "label_selection",
          columns: ["label"],
          settings: { type: "label_selection", options: [{ value: "a", text: "A", description: null }] },
          required: true,
          inserted_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
      ],
    }));
    const repository = new SchemaRepository(axios);

    const questions = await repository.getQuestions("s-1");

    expect(questions[0].type).toBe("label_selection");
    expect(questions[0].options).toEqual([{ value: "a", text: "A", description: null }]);
    expect(questions[0].required).toBe(true);
  });
});
