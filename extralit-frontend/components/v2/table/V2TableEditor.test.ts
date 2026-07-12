import { describe, expect, it } from "vitest";
import { ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import { tabulatorColumns, valueFromRowData } from "./V2TableEditor.vue";

describe("V2TableEditor column derivation", () => {
  it("derives one tabulator column per bound ColumnMeta with dtype-driven editors", () => {
    const columns = tabulatorColumns(
      [
        new ColumnMeta("name", "str", false, null),
        new ColumnMeta("count", "int64", false, null),
        new ColumnMeta("done", "bool", false, null),
        new ColumnMeta("when", "datetime64[ns]", true, null),
      ],
      true
    );

    expect(columns.map((c) => [c.field, c.editor])).toEqual([
      ["name", "input"],
      ["count", "number"],
      ["done", "tickCross"],
      ["when", "date"],
    ]);
  });

  it("honors the review overlay hint over the dtype default", () => {
    const columns = tabulatorColumns([new ColumnMeta("count", "int64", false, { type: "text" })], true);
    expect(columns[0].editor).toBe("input");
  });

  it("disables editors when not editable", () => {
    const columns = tabulatorColumns([new ColumnMeta("name", "str", false, null)], false);
    expect(columns[0].editor).toBe(false);
  });
});

describe("valueFromRowData", () => {
  it("keeps only bound-column keys (server validates keys ⊆ bound columns)", () => {
    const value = valueFromRowData({ name: "a", stray: "x" }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({ name: "a" });
  });

  it("drops undefined cells so absent keys stay absent", () => {
    const value = valueFromRowData({ name: undefined }, [new ColumnMeta("name", "str", false, null)]);
    expect(value).toEqual({});
  });
});
