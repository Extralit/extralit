import { describe, expect, it } from "vitest";
import { SuggestionHint } from "./SuggestionHint";

describe("SuggestionHint (leaf-widget suggestion duck-type)", () => {
  it("matches scalar values for single-select widgets", () => {
    const hint = new SuggestionHint("malaria", "gpt-4", 0.87, false);

    expect(hint.isSuggested("malaria")).toBe(true);
    expect(hint.isSuggested("dengue")).toBe(false);
    expect(hint.getSuggestion("malaria")).toEqual({ agent: "gpt-4", score: { fixed: "0.9" } });
  });

  it("matches membership for multi-select widgets", () => {
    const hint = new SuggestionHint(["a", "b"], null, null, true);

    expect(hint.isSuggested("a")).toBe(true);
    expect(hint.isSuggested("c")).toBe(false);
    expect(hint.getSuggestion("a")).toEqual({ agent: null, score: undefined });
  });
});
