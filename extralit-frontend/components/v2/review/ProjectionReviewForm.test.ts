import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ProjectionReviewForm from "./ProjectionReviewForm.vue";
import { ReferenceReview, ReviewCell, ReviewRecord } from "~/v2/domain/entities/review/ReferenceReview";
import { Question } from "~/v2/domain/entities/question/Question";

const textQuestion = new Question("q-size", "s-1", "size", "Sample size", null, "text", ["size"], {}, true);
const labelQuestion = new Question(
  "q-label",
  "s-1",
  "label",
  "Label",
  null,
  "label_selection",
  ["label"],
  {
    type: "label_selection",
    options: [{ value: "a", text: "A", description: null }],
  },
  false
);

const makeReview = (cells: ReviewCell[], draft = null, orphaned: { name: string; value: unknown }[] = []) =>
  new ReferenceReview("10.1000/j.x", [new ReviewRecord("r-1", "s-1", "sample_size", cells, [], orphaned, draft)], 1);

const stubs = {
  // Leaves are exercised in their own suites; here we assert dispatch + emit shaping.
  ContentEditableFeedbackTask: { template: "<div class='stub-text' />", props: ["value"] },
  LabelSelectionComponent: { template: "<div class='stub-label' />", props: ["modelValue"] },
  RatingMonoSelectionComponent: true,
  DndSelectionComponent: true,
  V2TableEditor: true,
};

describe("ProjectionReviewForm", () => {
  it("renders a widget per question type and suggestion provenance", () => {
    const review = makeReview([
      new ReviewCell(textQuestion, "12", "suggestion", { agent: "gpt", score: 0.9, suggestedValue: "12" }, false),
      new ReviewCell(labelQuestion, null, null, null, false),
    ]);

    const wrapper = mount(ProjectionReviewForm, { props: { review }, global: { stubs } });

    expect(wrapper.find(".stub-text").exists()).toBe(true);
    expect(wrapper.find(".stub-label").exists()).toBe(true);
    expect(wrapper.text()).toContain("review.suggestion");
    expect(wrapper.text()).toContain("gpt");
  });

  it("emits submit with (recordId, plain values) — page wraps them", async () => {
    const review = makeReview([
      new ReviewCell(textQuestion, "12", "suggestion", { agent: "gpt", score: 0.9, suggestedValue: "12" }, false),
    ]);
    const wrapper = mount(ProjectionReviewForm, { props: { review }, global: { stubs } });

    await wrapper.get("[data-test='submit-r-1']").trigger("click");

    expect(wrapper.emitted("submit")).toEqual([["r-1", { size: "12" }]]);
  });

  it("marks not-applicable cells and excludes them from emitted values", async () => {
    const review = makeReview([
      new ReviewCell(textQuestion, "12", "suggestion", null, false),
      new ReviewCell(labelQuestion, "a", "suggestion", null, true),
    ]);
    const wrapper = mount(ProjectionReviewForm, { props: { review }, global: { stubs } });

    expect(wrapper.text()).toContain("review.notApplicable");
    await wrapper.get("[data-test='save-draft-r-1']").trigger("click");
    expect(wrapper.emitted("save-draft")).toEqual([["r-1", { size: "12" }]]);
  });

  it("surfaces orphaned values read-only and never includes them in emits", async () => {
    const review = makeReview([new ReviewCell(textQuestion, "12", null, null, false)], null, [
      { name: "ghost", value: "zzz" },
    ]);
    const wrapper = mount(ProjectionReviewForm, { props: { review }, global: { stubs } });

    expect(wrapper.text()).toContain("review.orphanedValues");
    expect(wrapper.text()).toContain("ghost");
    await wrapper.get("[data-test='submit-r-1']").trigger("click");
    expect(wrapper.emitted("submit")![0][1]).not.toHaveProperty("ghost");
  });

  it("emits discard with the record id and renders submit errors passed back by the page", async () => {
    const review = makeReview([new ReviewCell(textQuestion, null, null, null, false)]);
    const wrapper = mount(ProjectionReviewForm, {
      props: { review, submitErrors: { "r-1": ["missing value for required question: size"] } },
      global: { stubs },
    });

    expect(wrapper.text()).toContain("missing value for required question: size");
    await wrapper.get("[data-test='discard-r-1']").trigger("click");
    expect(wrapper.emitted("discard")).toEqual([["r-1"]]);
  });
});
