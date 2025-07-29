<template>
  <div class="labels-selector">
    <BaseSearch v-model="searchText" :placeholder="$t('search')" />
    <div class="labels-selector__items">
      <BaseRadioButton
        class="labels-selector__item"
        v-for="({ name, numberOfDatasets }) in workspacesFilteredBySearchText"
        :key="name"
        :id="name"
        :name="name"
        :value="name"
        v-model="selectedWorkspaceValue"
      >
        {{ name }}
        <span class="labels-selector__number">({{ numberOfDatasets }})</span>
      </BaseRadioButton>
    </div>
  </div>
</template>
<script>
export default {
  props: {
    workspaces: {
      type: Array,
      required: true,
    },
    selectedWorkspace: {
      type: String,
      default: null,
    },
  },
  model: {
    prop: "selectedWorkspace",
    event: "input",
  },
  data: () => {
    return {
      searchText: "",
    };
  },
  computed: {
    selectedWorkspaceValue: {
      get() {
        return this.selectedWorkspace;
      },
      set(value) {
        this.$emit('input', value);
      }
    },
    workspacesFilteredBySearchText() {
      return this.workspaces.filter((workspace) =>
        workspace.name.toLowerCase().includes(this.searchText.toLowerCase())
      );
    },
  },
};
</script>
<style lang="scss" scoped>
.labels-selector {
  display: flex;
  flex-direction: column;
  &__items {
    max-height: 200px;
    overflow: auto;
    margin-top: $base-space;
  }
  &__item {
    &.radio-button {
      display: flex;
      padding: 6px $base-space;
      border-radius: $border-radius;
    }
    &--highlighted {
      background: var(--bg-opacity-4);
    }
    :deep(.radio-button__container) {
      background: none !important;
      border: 0 !important;
    }
    :deep(label) {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    &.radio-button :deep(.radio-button__container .svg-icon) {
      fill: var(--fg-cuaternary);
      min-width: 16px;
    }
  }
  &__number {
    @include font-size(12px);
  }
}
</style>
