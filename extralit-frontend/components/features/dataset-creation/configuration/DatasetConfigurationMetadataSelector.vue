<template>
  <div class="metadata-selector">
    <div class="metadata-selector__header">
      <span class="metadata-selector__subtitle">{{ $t("datasetCreation.metadataDescription") }}</span>
    </div>
    <div ref="optionsContainer" class="metadata-selector__options">
      <div
        v-for="fieldName in availableFields"
        :key="fieldName"
        :class="['metadata-selector__option', { 'metadata-selector__option--selected': isSelected(fieldName) }]"
        @click="toggleField(fieldName)"
      >
        <span class="metadata-selector__option-text">{{ fieldName }}</span>
        <svgicon v-if="isSelected(fieldName)" name="check" height="12" class="metadata-selector__option-icon" />
      </div>
    </div>
  </div>
</template>

<script lang="ts">

export default {
  props: {
    availableFields: {
      type: Array as () => string[],
      required: true,
    },
    selectedFields: {
      type: Array as () => string[],
      default: () => [],
    },
    defaultMetadataFields: {
      type: Array,
      default: () => ["reference", "doi", "pmid"],
    },
  },
  computed: {
    currentSelection() {
      return this.selectedFields.length > 0 ? this.selectedFields : this.getDefaultSelection();
    },
  },
  mounted() {
    // Initialize with default metadata fields if no selection exists
    if (this.selectedFields.length === 0) {
      this.$emit("onSelectionChange", this.getDefaultSelection());
    }
  },
  methods: {
    getDefaultSelection() {
      return this.availableFields.filter((field) => this.defaultMetadataFields.includes(field));
    },
    isSelected(fieldName) {
      return this.currentSelection.includes(fieldName);
    },
    toggleField(fieldName) {
      const newSelection = [...this.currentSelection];
      const index = newSelection.indexOf(fieldName);

      if (index > -1) {
        newSelection.splice(index, 1);
      } else {
        newSelection.push(fieldName);
      }

      this.$emit("onSelectionChange", newSelection);
    },
  },
};
</script>

<style lang="scss" scoped>
.metadata-selector {
  display: flex;
  flex-direction: column;
  gap: $base-space;

  &__header {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__title {
    font-weight: 500;
    @include font-size(14px);
    color: var(--fg-primary);
  }

  &__subtitle {
    @include font-size(12px);
    color: var(--fg-secondary);
    line-height: 1.4;
  }

  &__options {
    display: flex;
    gap: $base-space;
    overflow-x: auto;
    padding: calc($base-space / 2) 0;

    // Custom scrollbar styling
    &::-webkit-scrollbar {
      height: 4px;
    }

    &::-webkit-scrollbar-track {
      background: var(--bg-opacity-2);
      border-radius: 2px;
    }

    &::-webkit-scrollbar-thumb {
      background: var(--bg-opacity-6);
      border-radius: 2px;

      &:hover {
        background: var(--bg-opacity-8);
      }
    }
  }

  &__option {
    display: flex;
    align-items: center;
    gap: calc($base-space / 2);
    padding: calc($base-space / 2) $base-space;
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius;
    background: var(--bg-accent-grey-1);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
    flex-shrink: 0;
    transition: all 0.2s ease;

    &:hover {
      border-color: var(--bg-opacity-8);
      background: var(--bg-opacity-2);
    }

    &--selected {
      border-color: var(--bg-opacity-8);
      background: var(--bg-opacity-4);

      &:hover {
        border-color: var(--bg-opacity-8);
        background: var(--bg-opacity-4);
      }
    }
  }

  &__option-text {
    @include font-size(13px);
    font-weight: 400;
  }

  &__option-icon {
    color: var(--fg-primary);
    flex-shrink: 0;
  }
}
</style>
