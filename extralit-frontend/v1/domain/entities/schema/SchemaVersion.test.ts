import { describe, expect, it } from "vitest";
import { SchemaVersion } from "./SchemaVersion";

describe("SchemaVersion", () => {
  it("holds the version's identity fields (the column manifest lives on SchemaRepository.getColumns instead)", () => {
    const version = new SchemaVersion("v-1", "s-1", 1, "2026-01-01T00:00:00");

    expect(version).toMatchObject({
      id: "v-1",
      schemaId: "s-1",
      version: 1,
      insertedAt: "2026-01-01T00:00:00",
    });
  });
});
