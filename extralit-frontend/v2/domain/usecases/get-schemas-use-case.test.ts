import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { GetSchemasUseCase } from "./get-schemas-use-case";
import { Schema } from "../entities/schema/Schema";
import { useSchemas } from "~/v2/infrastructure/storage/SchemasStorage";

const SCHEMA = new Schema("s-1", "sample_size", "published", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");

describe("GetSchemasUseCase", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("fetches schemas and saves them to storage", async () => {
    const repository = { getSchemas: vi.fn(async () => [SCHEMA]) };
    // Pass the resolved store object, matching what ts-injecty injects at runtime.
    const useCase = new GetSchemasUseCase(repository as never, useSchemas());

    const result = await useCase.execute("w-1");

    expect(repository.getSchemas).toHaveBeenCalledWith("w-1");
    expect(result).toEqual([SCHEMA]);
    expect(useSchemas().get().schemas).toEqual([SCHEMA]);
  });
});
