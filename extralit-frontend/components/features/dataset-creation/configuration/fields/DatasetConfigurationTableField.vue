<template>
  <div class="table-field-config">
    <div class="table-field-config__preview">
      <div class="table-field-config__preview-header">
        <div
          v-for="col in previewColumns"
          :key="col"
          class="table-field-config__preview-cell table-field-config__preview-cell--header"
        >
          {{ col }}
        </div>
      </div>
      <div
        v-for="row in previewRows"
        :key="row"
        class="table-field-config__preview-row"
      >
        <div
          v-for="col in previewColumns"
          :key="col"
          class="table-field-config__preview-cell"
        >
          <span class="table-field-config__preview-placeholder" />
        </div>
      </div>
    </div>
    <label
      class="table-field-config__help"
      v-text="$t('datasetCreation.fields.table.helpText')"
    />
  </div>
</template>

<script>
export default {
  props: {
    field: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      previewColumns: ["Column A", "Column B", "Column C"],
      previewRows: [1, 2],
    };
  },
};
</script>

<style lang="scss" scoped>
.table-field-config {
  display: flex;
  flex-direction: column;
  gap: $base-space;

  &__preview {
    border: 1px solid var(--bg-opacity-10);
    border-radius: $border-radius;
    overflow: hidden;
  }

  &__preview-header {
    display: flex;
    background: var(--bg-accent-grey-2);
    border-bottom: 1px solid var(--bg-opacity-10);
  }

  &__preview-row {
    display: flex;
    border-bottom: 1px solid var(--bg-opacity-6);

    &:last-child {
      border-bottom: none;
    }
  }

  &__preview-cell {
    flex: 1;
    padding: calc($base-space / 2) $base-space;
    @include font-size(11px);
    color: var(--fg-tertiary);
    border-right: 1px solid var(--bg-opacity-6);
    min-height: calc($base-space * 3.5);
    display: flex;
    align-items: center;

    &:last-child {
      border-right: none;
    }

    &--header {
      font-weight: 600;
      color: var(--fg-secondary);
      @include font-size(11px);
    }
  }

  &__preview-placeholder {
    display: block;
    height: 8px;
    width: 70%;
    background: var(--bg-opacity-6);
    border-radius: $border-radius;
  }

  &__help {
    color: var(--fg-secondary);
    @include font-size(12px);
  }
}
</style>
