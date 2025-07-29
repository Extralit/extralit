<template>
  <div class="datasets-filter" v-if="workspaces.length">
    <BaseDropdown :visible="visibleDropdown" @visibility="onToggleVisibility">
      <span slot="dropdown-header"
        ><WorkspacesFilterButton :is-active="visibleDropdown || !!selectedWorkspace"
      /></span>
      <span slot="dropdown-content" class="datasets-filter__container">
        <div class="datasets-filter__content">
          <WorkspaceSelector :workspaces="workspaces" :selected-workspace="selectedWorkspace" />
        </div>
      </span>
    </BaseDropdown>
  </div>
</template>

<script>
import "assets/icons/chevron-left";

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
    event: "on-change-workspace-filter",
  },
  data() {
    return {
      visibleDropdown: false,
    };
  },
  watch: {
    selectedWorkspace() {
      this.$emit("on-change-workspace-filter", this.selectedWorkspace);
    },
  },
  methods: {
    onToggleVisibility(value) {
      this.visibleDropdown = value;
    },
  },
};
</script>
<style lang="scss" scoped>
$datasets-filter-width: 120px;
$datasets-filter-max-width: 300px;
.datasets-filter {
  &__container {
    display: block;
    width: auto;
    max-width: $datasets-filter-max-width;
  }
  &__header {
    display: flex;
    gap: $base-space;
    align-items: center;
    justify-content: space-between;
    padding: $base-space $base-space * 2;
    cursor: pointer;
    &:hover {
      background: var(--bg-opacity-4);
    }
  }
  &__content {
    padding: $base-space;
  }
  &__categories {
    padding: $base-space;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
  }
  &__button.button {
    padding: 10px;
  }
  :deep(.dropdown__header:hover) {
    background: none;
  }
  :deep(.dropdown__content) {
    right: 0;
    left: auto;
  }
}
</style>
