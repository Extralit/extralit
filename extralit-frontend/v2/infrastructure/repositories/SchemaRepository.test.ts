import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { SchemaRepository } from "./SchemaRepository";

const axiosMock = (getImpl: (url: string) => unknown) =>
  ({ get: vi.fn(async (url: string) => ({ data: getImpl(url) })) }) as unknown as AxiosInstance;

const BACKEND_DATASET = {
  id: "s-1",
  name: "sample_size",
  status: "ready",
  current_schema_version_id: "v-1",
  settings: {},
  workspace_id: "w-1",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-01T00:00:00",
};

describe("SchemaRepository", () => {
  it("lists schemas for a workspace and maps to domain entities", async () => {
    const axios = axiosMock(() => ({ items: [BACKEND_DATASET] }));
    const repository = new SchemaRepository(axios);

    const schemas = await repository.getSchemas("w-1");

    expect(axios.get).toHaveBeenCalledWith("/v1/me/datasets", { params: { workspace_id: "w-1" } });
    expect(schemas[0].workspaceId).toBe("w-1");
    expect(schemas[0].currentVersionId).toBe("v-1");
  });

  it("filters out datasets with no current schema version (plain annotation datasets)", async () => {
    const axios = axiosMock(() => ({
      items: [BACKEND_DATASET, { ...BACKEND_DATASET, id: "s-2", current_schema_version_id: null }],
    }));
    const repository = new SchemaRepository(axios);

    const schemas = await repository.getSchemas("w-1");

    expect(schemas.map((s) => s.id)).toEqual(["s-1"]);
  });

  it("fetches a single schema and maps it to a domain entity", async () => {
    const axios = axiosMock(() => BACKEND_DATASET);
    const repository = new SchemaRepository(axios);

    const schema = await repository.getSchema("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v1/datasets/s-1");
    expect(schema.id).toBe("s-1");
    expect(schema.name).toBe("sample_size");
    expect(schema.currentVersionId).toBe("v-1");
  });

  it("maps schema versions without a column manifest (that now comes from getColumns)", async () => {
    const axios = axiosMock(() => [
      {
        id: "v-1",
        dataset_id: "s-1",
        version: 1,
        object_key: "k",
        object_version_id: null,
        etag: "e",
        checksum: "c",
        parent_version_id: null,
        created_by: null,
        inserted_at: "2026-01-01T00:00:00",
        updated_at: "2026-01-01T00:00:00",
      },
    ]);
    const repository = new SchemaRepository(axios);

    const versions = await repository.getVersions("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v1/datasets/s-1/schema-versions");
    expect(versions[0]).toMatchObject({ id: "v-1", schemaId: "s-1", version: 1 });
  });

  it("maps questions reading type and columns out of settings, not the top level", async () => {
    const axios = axiosMock(() => ({
      items: [
        {
          id: "q-1",
          dataset_id: "s-1",
          name: "label",
          title: "Label",
          description: null,
          required: true,
          settings: { type: "label_selection", options: [{ value: "a", text: "A", description: null }] },
          inserted_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
        {
          id: "q-2",
          dataset_id: "s-1",
          name: "notes",
          title: "Notes",
          description: null,
          required: false,
          settings: { type: "text", columns: ["title"] },
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
    expect(questions[0].columns).toBeNull();
    expect(questions[1].type).toBe("text");
    expect(questions[1].columns).toEqual(["title"]);
  });

  it("builds the column manifest from column-type fields, filtering out non-column fields", async () => {
    const axios = axiosMock(() => ({
      items: [
        {
          id: "f-1",
          name: "title",
          title: "Title",
          required: true,
          settings: { type: "column", dtype: "str", nullable: false, review: { type: "text" } },
          dataset_id: "s-1",
          inserted_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
        {
          id: "f-2",
          name: "body",
          title: "Body",
          required: true,
          settings: { type: "text", use_markdown: false, use_table: false },
          dataset_id: "s-1",
          inserted_at: "2026-01-01T00:00:00",
          updated_at: "2026-01-01T00:00:00",
        },
      ],
    }));
    const repository = new SchemaRepository(axios);

    const columns = await repository.getColumns("s-1");

    expect(axios.get).toHaveBeenCalledWith("/v1/datasets/s-1/fields");
    expect(columns).toHaveLength(1);
    expect(columns[0]).toMatchObject({ name: "title", dtype: "str", nullable: false, review: { type: "text" } });
  });
});
