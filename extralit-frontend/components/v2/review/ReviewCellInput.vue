<template>
  <div class="review-cell" :data-question="cell.question.name">
    <label class="review-cell__title">
      {{ cell.question.title }}
      <span v-if="cell.question.required" class="review-cell__required">*</span>
    </label>
    <ReviewProvenance v-if="cell.source" :source="cell.source" :provenance="cell.provenance" />

    <p v-if="cell.notApplicable" class="review-cell__na" v-text="$t('review.notApplicable')" />

    <template v-else>
      <ContentEditableFeedbackTask
        v-if="cell.question.type === 'text'"
        :value="String(modelValue ?? '')"
        :original-value="String(cell.value ?? '')"
        @change-text="$emit('update:modelValue', $event)"
      />

      <LabelSelectionComponent
        v-else-if="cell.question.isLabelType"
        v-model="labelOptions"
        :component-id="cell.question.id"
        :multiple="cell.question.type === 'multi_label_selection'"
        :suggestion="suggestionHint"
        :visible-shortcuts="false"
        @on-selected="onLabelChanged"
      />

      <RatingMonoSelectionComponent
        v-else-if="cell.question.type === 'rating'"
        v-model="ratingOptions"
        :suggestion="suggestionHint"
        @on-selected="onRatingChanged"
      />

      <DndSelectionComponent
        v-else-if="cell.question.type === 'ranking'"
        :ranking="ranking"
        :suggestion="suggestionHint"
        @on-reorder="onReordered"
      />

      <V2TableEditor
        v-else-if="cell.question.type === 'table'"
        :model-value="(modelValue as Record<string, unknown>) ?? {}"
        :columns="tableColumns"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </template>
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, ref, watch, type PropType } from "vue";
import { type ReviewCell } from "~/v2/domain/entities/review/ReferenceReview";
import { type ColumnMeta } from "~/v2/domain/entities/schema/ColumnMeta";
import {
  buildLabelOptions,
  buildRankingValues,
  buildRatingOptions,
  rankingAnswerFromValues,
  selectedFromLabelOptions,
  selectedFromRatingOptions,
  suggestionHintFor,
} from "~/v2/domain/entities/review/widget-adapters";
import { adaptQuestionsToSlots } from "@/components/base/inputs/ranking/ranking-adapter";
// Explicit imports (not Nuxt auto-import) so plain vitest `mount` resolves the children
// and name-based `global.stubs` can replace them.
import ReviewProvenance from "./ReviewProvenance.vue";
import ContentEditableFeedbackTask from "@/components/base/inputs/text-area/ContentEditableFeedbackTask.vue";
import LabelSelectionComponent from "@/components/base/inputs/label-selection/LabelSelection.component.vue";
import RatingMonoSelectionComponent from "@/components/base/inputs/rating/RatingMonoSelection.component.vue";
import DndSelectionComponent from "@/components/base/inputs/ranking/DndSelection.component.vue";
import V2TableEditor from "@/components/v2/table/V2TableEditor.vue";

export default defineComponent({
  name: "ReviewCellInput",
  components: {
    ReviewProvenance,
    ContentEditableFeedbackTask,
    LabelSelectionComponent,
    RatingMonoSelectionComponent,
    DndSelectionComponent,
    V2TableEditor,
  },
  props: {
    cell: { type: Object as PropType<ReviewCell>, required: true },
    modelValue: { type: null as unknown as PropType<unknown>, default: null },
    // table questions: the bound columns' ColumnMeta from the pinned version cache
    tableColumns: { type: Array as PropType<ColumnMeta[]>, default: () => [] },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const question = props.cell.question;
    const suggestionHint = computed(() => suggestionHintFor(props.cell));

    // Leaves mutate their option arrays in place; hold them locally and translate on change.
    const labelOptions = ref(buildLabelOptions(question, props.modelValue));
    const ratingOptions = ref(buildRatingOptions(question, props.modelValue));
    const rankingValues = ref(buildRankingValues(question, props.modelValue));
    const ranking = computed(() => adaptQuestionsToSlots({ options: rankingValues.value }));

    watch(
      () => props.modelValue,
      (value) => {
        // External resets (draft restore / discard) — rebuild local option state.
        labelOptions.value = buildLabelOptions(question, value);
        ratingOptions.value = buildRatingOptions(question, value);
        rankingValues.value = buildRankingValues(question, value);
      }
    );

    const onLabelChanged = () =>
      emit(
        "update:modelValue",
        selectedFromLabelOptions(labelOptions.value, question.type === "multi_label_selection")
      );
    const onRatingChanged = () => emit("update:modelValue", selectedFromRatingOptions(ratingOptions.value));
    const onReordered = (newRanking: { getRanking(option: unknown): number | undefined }) => {
      rankingValues.value.forEach((option) => {
        option.rank = newRanking.getRanking(option) ?? null;
      });
      emit("update:modelValue", rankingAnswerFromValues(rankingValues.value));
    };

    return { suggestionHint, labelOptions, ratingOptions, ranking, onLabelChanged, onRatingChanged, onReordered };
  },
});
</script>

<style lang="scss" scoped>
.review-cell {
  display: flex;
  flex-direction: column;
  gap: $base-space;
  margin-bottom: $base-space * 2;

  &__title {
    font-weight: 500;
  }

  &__required {
    color: var(--color-danger, #c00);
  }

  &__na {
    color: var(--fg-tertiary);
    font-style: italic;
  }
}
</style>
