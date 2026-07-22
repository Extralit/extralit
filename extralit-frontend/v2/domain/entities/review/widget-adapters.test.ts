import { describe, expect, it } from "vitest";
import { Question } from "../question/Question";
import { ReviewCell } from "./ReviewCell";
import {
  buildLabelOptions,
  buildRankingValues,
  buildRatingOptions,
  rankingAnswerFromValues,
  selectedFromLabelOptions,
  selectedFromRatingOptions,
  suggestionHintFor,
} from "./widget-adapters";

const labelQuestion = new Question(
  "q-1",
  "s-1",
  "label",
  "Label",
  null,
  "label_selection",
  ["label"],
  {
    type: "label_selection",
    options: [
      { value: "a", text: "A", description: null },
      { value: "b", text: "B", description: null },
    ],
  },
  false
);

const ratingQuestion = new Question(
  "q-2",
  "s-1",
  "stars",
  "Stars",
  null,
  "rating",
  ["stars"],
  {
    type: "rating",
    options: [{ value: 1 }, { value: 2 }, { value: 3 }],
  },
  false
);

const rankingQuestion = new Question(
  "q-3",
  "s-1",
  "rank",
  "Rank",
  null,
  "ranking",
  ["rank"],
  {
    type: "ranking",
    options: [
      { value: "x", text: "X", description: null },
      { value: "y", text: "Y", description: null },
    ],
  },
  false
);

describe("label adapters", () => {
  it("builds leaf options with isSelected from a scalar (single) or array (multi) value", () => {
    expect(buildLabelOptions(labelQuestion, "b").map((o) => o.isSelected)).toEqual([false, true]);
    expect(buildLabelOptions(labelQuestion, ["a", "b"]).map((o) => o.isSelected)).toEqual([true, true]);
    expect(buildLabelOptions(labelQuestion, null).map((o) => o.isSelected)).toEqual([false, false]);
  });

  it("derives the server value shape back from options", () => {
    const options = buildLabelOptions(labelQuestion, "b");
    expect(selectedFromLabelOptions(options, false)).toBe("b");
    expect(selectedFromLabelOptions(options, true)).toEqual(["b"]);
    expect(selectedFromLabelOptions(buildLabelOptions(labelQuestion, null), false)).toBeNull();
  });
});

describe("rating adapters", () => {
  it("round-trips a numeric rating", () => {
    const options = buildRatingOptions(ratingQuestion, 2);
    expect(options).toEqual([
      { id: "stars_1", value: 1, isSelected: false },
      { id: "stars_2", value: 2, isSelected: true },
      { id: "stars_3", value: 3, isSelected: false },
    ]);
    expect(selectedFromRatingOptions(options)).toBe(2);
  });
});

describe("ranking adapters", () => {
  it("round-trips the [{value, rank}] server shape", () => {
    const values = buildRankingValues(rankingQuestion, [{ value: "y", rank: 1 }]);
    expect(values.find((v) => v.value === "y")?.rank).toBe(1);
    expect(values.find((v) => v.value === "x")?.rank).toBeNull();

    values.find((v) => v.value === "x")!.rank = 2;
    expect(rankingAnswerFromValues(values)).toEqual([
      { value: "y", rank: 1 },
      { value: "x", rank: 2 },
    ]);
  });
});

describe("suggestionHintFor", () => {
  it("returns a hint only for suggestion-sourced cells", () => {
    const suggested = new ReviewCell(
      labelQuestion,
      "a",
      "suggestion",
      { agent: "gpt", score: 0.5, suggestedValue: "a" },
      false
    );
    const responded = new ReviewCell(labelQuestion, "a", "response", null, false);

    expect(suggestionHintFor(suggested)?.isSuggested("a")).toBe(true);
    expect(suggestionHintFor(responded)).toBeNull();
  });
});
