import { describe, expect, it } from "vitest";
import { ColumnMeta } from "./ColumnMeta";
import { SchemaVersion } from "./SchemaVersion";

describe("SchemaVersion", () => {
  const version = new SchemaVersion(
    "v-1",
    "s-1",
    1,
    [new ColumnMeta("title", "str", false, null)],
    {},
    "2026-01-01T00:00:00"
  );

  it("finds a cached column by name", () => {
    expect(version.findColumn("title")?.dtype).toBe("str");
  });

  it("returns undefined for a column missing from this version's cache (old-version tolerance)", () => {
    expect(version.findColumn("added_later")).toBeUndefined();
  });
});
