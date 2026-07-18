import { describe, expect, it } from "vitest";
import { ColumnMeta } from "../schema/ColumnMeta";
import { columnCellEditor, contextRenderer, dtypeDefaultEditor } from "./widget-mapping";

describe("dtypeDefaultEditor", () => {
  it.each([
    ["str", "text"],
    ["int64", "number"],
    ["int32", "number"],
    ["float64", "number"],
    ["bool", "checkbox"],
    ["datetime64[ns]", "date"],
    ["object", "text"], // unknown dtype falls back to text
    ["interval[int64]", "text"], // "int" prefix must not classify interval as number
    ["uint8", "number"],
  ])("maps dtype %s to %s", (dtype, editor) => {
    expect(dtypeDefaultEditor(dtype)).toBe(editor);
  });
});

describe("columnCellEditor (§6.2 precedence)", () => {
  it("uses review.type when it is a known editor", () => {
    const column = new ColumnMeta("score", "float64", true, { type: "text" });
    expect(columnCellEditor(column)).toBe("text");
  });

  it("falls back to dtype default when review.type is unknown (forward-compatible overlay)", () => {
    const column = new ColumnMeta("score", "float64", true, { type: "sparkline" });
    expect(columnCellEditor(column)).toBe("number");
  });

  it("falls back to dtype default when review is null", () => {
    const column = new ColumnMeta("done", "bool", false, null);
    expect(columnCellEditor(column)).toBe("checkbox");
  });
});

describe("contextRenderer (§6.3)", () => {
  it("mirrors the same precedence for read-only context fields", () => {
    expect(contextRenderer(new ColumnMeta("when", "datetime64[ns]", true, null))).toBe("date");
    expect(contextRenderer(new ColumnMeta("when", "datetime64[ns]", true, { type: "text" }))).toBe("text");
  });
});
