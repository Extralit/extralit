import { describe, expect, it } from "vitest";
import { unwrapResponseValues, wrapResponseValues } from "./response-values";

describe("response value wrapping (spec §7 asymmetric-wrapping gotcha)", () => {
  it("wraps plain values into {question_name: {value}}", () => {
    expect(wrapResponseValues({ size: 12, label: "a" })).toEqual({
      size: { value: 12 },
      label: { value: "a" },
    });
  });

  it("unwraps the double-wrapped GET shape", () => {
    expect(unwrapResponseValues({ size: { value: 12 } })).toEqual({ size: 12 });
  });

  it("unwraps null (no response yet) to an empty object", () => {
    expect(unwrapResponseValues(null)).toEqual({});
  });

  it("round-trips", () => {
    const values = { a: [1, 2], b: { c: true } };
    expect(unwrapResponseValues(wrapResponseValues(values))).toEqual(values);
  });
});
