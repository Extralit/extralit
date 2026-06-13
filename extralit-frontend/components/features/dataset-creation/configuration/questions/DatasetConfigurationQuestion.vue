<template>
  <DatasetConfigurationCard
    :item="question"
    config-type="question"
    :available-types="availableTypes"
    @is-focused="$emit('is-focused', $event)"
    @change-type="$emit('change-type', $event)"
    @name-changed="updateQuestionName"
  >
    <BaseButton v-if="removeIsAllowed" class="config-card__remove" @click="remove"><svgicon name="close" /></BaseButton>

    <template v-if="noMapping">
      <DatasetConfigurationLabels
        v-if="question.settings.type.isSingleLabelType || question.settings.type.isMultiLabelType"
        :question="question"
        @is-focused="$emit('is-focused', $event)"
      />
      <DatasetConfigurationSpan
        v-else-if="question.settings.type.isSpanType"
        :question="question"
        :textFields="selectedSubset.textFields"
        @is-focused="$emit('is-focused', $event)"
      />
      <DatasetConfigurationRating
        v-else-if="question.settings.type.isRatingType"
        :question="question"
        @is-focused="$emit('is-focused', $event)"
      />
      <DatasetConfigurationRanking
        v-else-if="question.settings.type.isRankingType"
        :value="question.settings.options"
        @on-value-change="question.settings.options = $event"
        @is-focused="$emit('is-focused', $event)"
      />
    </template>
    <span class="separator"></span>
    <DatasetConfigurationColumnSelector
      v-if="showColumnSelector"
      :value="question.column"
      @onValueChange="question.column = $event"
      class="config-card__type"
      :options="selectedSubset.columns"
    />
    <BaseCheckbox
      class="config-card__required"
      :value="question.required"
      @input="question.required = !question.required"
    >
      {{ $t("datasetCreation.requiredQuestion") }}</BaseCheckbox
    >
  </DatasetConfigurationCard>
</template>

<script lang="ts">
export default {
  props: {
    question: {
      type: Object,
      required: true,
    },
    selectedSubset: {
      type: Object,
      required: true,
    },
    removeIsAllowed: {
      type: Boolean,
      default: false,
    },
    availableTypes: {
      type: Array,
      required: true,
    },
  },
  model: {
    prop: "type",
    event: "change",
  },
  computed: {
    noMapping() {
      return this.question.column === "no mapping";
    },
    showColumnSelector() {
      return this.question.wasAutoMapped || this.question.isTextType;
    },
  },
  methods: {
    remove() {
      this.selectedSubset.removeQuestion(this.question.name);
    },
    updateQuestionName(newName: string) {
      try {
        // Rename the question in the subset - this will replace the question object
        this.selectedSubset.renameQuestion(this.question.name, newName);
      } catch (error) {
        console.error('Failed to rename question:', error.message);
        // You could show a user-friendly error message here
      }
    },
  },
};
</script>
<style lang="scss" scoped>
.config-card {
  &__remove.button {
    position: absolute;
    top: $base-space * 1.5;
    right: $base-space * 1.5;
    padding: 0;
  }
  &__required {
    display: flex;
    gap: $base-space;
    @include font-size(12px);
    flex-flow: row-reverse;
    justify-content: flex-end;
    &:deep(.checkbox__container) {
      margin: 0;
      border-color: var(--bg-opacity-20);
      background: var(--bg-accent-grey-1);
    }
  }
  .separator {
    width: 100%;
    height: 1px;
    background: var(--bg-opacity-6);
    margin-top: $base-space;
  }
}
</style>
