<template>
  <div
    class="labels-selector"
    @keyup.enter="includePreselectedOption"
    @keyup.up="preselectPreviousOption"
    @keyup.down="preselectNextOption"
  >
    <BaseSearch v-model="searchText" :placeholder="$t('search')" />
    <div class="labels-selector__items">
      <BaseRadioButton
        class="labels-selector__item"
        :class="index === preSelectionIndex ? 'labels-selector__item--highlighted' : null"
        v-for="({ name, numberOfDatasets }, index) in workspacesFilteredBySearchText"
        :key="name"
        :value="name"
        :checked="selectedWorkspace === name"
        @change="selectWorkspace(name)"
        @mouseover.native="preSelectionIndex = index"
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
      preSelectionIndex: 0,
    };
  },
  watch: {
    searchText() {
      this.preSelectionIndex = 0;
    },
  },
  computed: {
    workspacesFilteredBySearchText() {
      return this.workspaces.filter((workspace) =>
        workspace.name.toLowerCase().includes(this.searchText.toLowerCase())
      );
    },
    workspacesLength() {
      return this.workspaces.length;
    },
  },
  methods: {
    includePreselectedOption() {
      if (!this.workspacesFilteredBySearchText.length) return;

      this.selectWorkspace(this.workspacesFilteredBySearchText[this.preSelectionIndex].name);

      this.preSelectionIndex = 0;
    },
    selectWorkspace(workspaceName) {
      // Toggle selection - if already selected, deselect
      if (this.selectedWorkspace === workspaceName) {
        this.$emit('input', null);
      } else {
        this.$emit('input', workspaceName);
      }
    },
    preselectNextOption() {
      this.preSelectionIndex === this.workspacesLength - 1 ? (this.preSelectionIndex = 0) : this.preSelectionIndex++;
    },
    preselectPreviousOption() {
      this.preSelectionIndex === 0 ? (this.preSelectionIndex = this.workspacesLength - 1) : this.preSelectionIndex--;
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
