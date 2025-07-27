<template>
  <div class="fields__header">
    <div class="fields__header--left">
      <BaseCheckbox
        v-if="Array.isArray(selectedRecords)"
        :data-title="$t('select')"
        class="fields__checkbox"
        :decoration-circle="recordCriteria.isComingToBulkMode"
        :value="selectedRecords.includes(record)"
        @input="onSelectedRecord"
      />
      <BaseBadge v-if="record.metadata?.reference" :text="`${record.metadata?.reference}`" />
      <BaseTag v-if="record.metadata?.number" :name="record.metadata?.number" />
      <BaseTag v-else-if="record.metadata?.type" :name="record.metadata?.type" />
    </div>
    <div class="fields__header--right">
      <SimilarityScorePercentage
        v-if="recordCriteria.isFilteringBySimilarity && record.score.percentage"
        class="similarity__progress"
        :value="record.score.percentage"
        :data-title="$t('similarity.similarityScore')"
      >
      </SimilarityScorePercentage>
      <SimilarityFilter
        v-if="datasetVectors.length"
        :availableVectors="datasetVectors"
        :recordCriteria="recordCriteria"
        :recordId="record.id"
      />
      <RecordStatus :record="record" />
      <RecordMenu :record="record" />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    record: {
      type: Object,
      required: true,
    },
    recordCriteria: {
      type: Object,
      required: true,
    },
    datasetVectors: {
      type: Array,
      default: () => [],
    },
    selectedRecords: {
      type: Array,
    },
  },
  methods: {
    onSelectedRecord(isSelected) {
      this.$emit("on-select-record", isSelected, this.record);
    },
  },
};
</script>

<style lang="scss" scoped>
.fields {
  &__header {
    $this: &;
    border-radius: $border-radius-m;
    background: var(--bg-accent-grey-1);
    display: flex;
    justify-content: space-between;
    #{$this}__header {
      padding: $base-space $base-space * 2;
    }

    &--left,
    &--right {
      display: flex;
      align-items: center;
      gap: $base-space;
    }

    &--right {
      margin-left: auto;
    }
  }
  &__checkbox {
    &:not(.checked):hover {
      :deep(.checkbox__container) {
        border-color: var(--fg-tertiary);
      }
    }
    :deep(.checkbox__container) {
      border-color: var(--bg-opacity-20);
    }
  }
}

.fields__header {
  position: relative;
  min-width: 0;

  &--left {
    flex-shrink: 1;
    min-width: 0;
    overflow: hidden;
  }

  &--right {
    flex-shrink: 0;
    z-index: 2;
  }
}

.similarity__progress {
  &[data-title] {
    position: relative;
    @include tooltip-mini("bottom");
    cursor: default;
  }
}
.fields__checkbox[data-title] {
  position: relative;
  overflow: visible;
  @include tooltip-mini("right", 12px);
}
</style>
