<template>
  <div class="datasets-filter" v-if="workspaces.length">
    <BaseDropdown :visible="visibleDropdown" @visibility="onToggleVisibility">
      <span slot="dropdown-header"
        ><WorkspacesFilterButton
          :is-active="visibleDropdown || !!localSelectedWorkspace"
          :selected-workspace="localSelectedWorkspace"
        /></span>
      <span slot="dropdown-content" class="datasets-filter__container">
        <div class="datasets-filter__content">
          <WorkspaceSelector
            :workspaces="workspaces"
            v-model="localSelectedWorkspace"
          />
        </div>
      </span>
    </BaseDropdown>
  </div>
</template>

<script lang="ts">
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
      localSelectedWorkspace: this.selectedWorkspace,
    };
  },
  watch: {
    selectedWorkspace(newValue: string) {
      this.localSelectedWorkspace = newValue;
    },
    localSelectedWorkspace(newValue: string) {
      this.$emit("on-change-workspace-filter", newValue);
    },
    workspaces: {
      immediate: true,
      handler(newWorkspaces) {
        // Auto-assign the first workspace if none is selected and workspaces exist
        if (!this.localSelectedWorkspace && newWorkspaces && newWorkspaces.length > 0) {
          this.localSelectedWorkspace = newWorkspaces[0].name;
        }
      }
    }
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
