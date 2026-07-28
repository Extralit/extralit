import { describe, expect, it, vi } from "vitest";
import { GetSchemaSettingsUseCase } from "./get-schema-settings-use-case";
import { Schema } from "../entities/schema/Schema";
import { SchemaVersion } from "../entities/schema/SchemaVersion";
import { Question } from "../entities/schema/Question";
import { ColumnMeta } from "../entities/schema/ColumnMeta";

const SCHEMA = new Schema("s-1", "sample_size", "ready", "w-1", "v-1", {}, "2026-01-01", "2026-01-01");
const VERSION = new SchemaVersion("v-1", "s-1", 1, "2026-01-01");
const QUESTION = new Question("q-1", "s-1", "label", "Label", null, "label_selection", null, {}, true);
const COLUMN = new ColumnMeta("title", "str", false, null);

describe("GetSchemaSettingsUseCase", () => {
  it("fans out all four repository calls and returns the assembled settings shape", async () => {
    const repository = {
      getSchema: vi.fn(async () => SCHEMA),
      getVersions: vi.fn(async () => [VERSION]),
      getQuestions: vi.fn(async () => [QUESTION]),
      getColumns: vi.fn(async () => [COLUMN]),
    };
    const useCase = new GetSchemaSettingsUseCase(repository as never);

    const result = await useCase.execute("s-1");

    expect(repository.getSchema).toHaveBeenCalledWith("s-1");
    expect(repository.getVersions).toHaveBeenCalledWith("s-1");
    expect(repository.getQuestions).toHaveBeenCalledWith("s-1");
    expect(repository.getColumns).toHaveBeenCalledWith("s-1");
    expect(result).toEqual({ schema: SCHEMA, versions: [VERSION], questions: [QUESTION], columns: [COLUMN] });
  });
});
