import { describe, expect, it } from "vitest";
import { defineComponent, h } from "vue";
import { mount } from "@vue/test-utils";
import ReviewCellInput from "./ReviewCellInput.vue";
import { ReviewCell } from "~/v2/domain/entities/review/ReviewCell";
import { Question } from "~/v2/domain/entities/question/Question";

// Stubs that actually emit the leaf-widget events (the real leaves mutate their bound
// option array in place, then emit on-selected/on-reorder) so the adapter-invocation
// wiring in ReviewCellInput's handlers is exercised end-to-end (roborev job 150).
const LabelStub = defineComponent({
  props: ["modelValue", "multiple"],
  emits: ["on-selected", "update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h("button", {
        class: "label-emit",
        onClick: () => {
          props.modelValue[0].isSelected = true; // pick option "a" in place
          emit("on-selected");
        },
      });
  },
});

const RatingStub = defineComponent({
  props: ["modelValue"],
  emits: ["on-selected", "update:modelValue"],
  setup(props, { emit }) {
    return () =>
      h("button", {
        class: "rating-emit",
        onClick: () => {
          props.modelValue[1].isSelected = true; // pick value 2 in place
          emit("on-selected");
        },
      });
  },
});

const RankingStub = defineComponent({
  props: ["ranking"],
  emits: ["on-reorder"],
  setup(_props, { emit }) {
    return () =>
      h("button", {
        class: "ranking-emit",
        // Fake reorder result: x -> rank 1, y -> rank 2.
        onClick: () => emit("on-reorder", { getRanking: (o: { value: string }) => (o.value === "x" ? 1 : 2) }),
      });
  },
});

const labelOptions = [
  { value: "a", text: "A", description: null },
  { value: "b", text: "B", description: null },
];

const mountCell = (question: Question, stubs: Record<string, unknown>) =>
  mount(ReviewCellInput, {
    props: { cell: new ReviewCell(question, null, null, null, false) },
    global: { stubs },
  });

describe("ReviewCellInput widget-event wiring", () => {
  it("emits a scalar value for single label_selection", async () => {
    const q = new Question(
      "q",
      "s",
      "label",
      "Label",
      null,
      "label_selection",
      ["label"],
      {
        type: "label_selection",
        options: labelOptions,
      },
      false
    );
    const wrapper = mountCell(q, { LabelSelectionComponent: LabelStub });

    await wrapper.get(".label-emit").trigger("click");

    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["a"]);
  });

  it("emits an array value for multi_label_selection (multiple flag wired)", async () => {
    const q = new Question(
      "q",
      "s",
      "label",
      "Label",
      null,
      "multi_label_selection",
      ["label"],
      {
        type: "multi_label_selection",
        options: labelOptions,
      },
      false
    );
    const wrapper = mountCell(q, { LabelSelectionComponent: LabelStub });

    await wrapper.get(".label-emit").trigger("click");

    expect(wrapper.emitted("update:modelValue")![0]).toEqual([["a"]]);
  });

  it("emits the numeric rating value", async () => {
    const q = new Question(
      "q",
      "s",
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
    const wrapper = mountCell(q, { RatingMonoSelectionComponent: RatingStub });

    await wrapper.get(".rating-emit").trigger("click");

    expect(wrapper.emitted("update:modelValue")![0]).toEqual([2]);
  });

  it("emits the [{value, rank}] server shape from a reorder", async () => {
    const q = new Question(
      "q",
      "s",
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
    const wrapper = mountCell(q, { DndSelectionComponent: RankingStub });

    await wrapper.get(".ranking-emit").trigger("click");

    expect(wrapper.emitted("update:modelValue")![0]).toEqual([
      [
        { value: "x", rank: 1 },
        { value: "y", rank: 2 },
      ],
    ]);
  });
});
