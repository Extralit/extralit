<template>
  <div class="workspace-breadcrumb-dropdown">
    <BaseDropdown :visible="visibleDropdown" @visibility="onToggleVisibility">
      <span
        slot="dropdown-header"
        class="workspace-breadcrumb-dropdown__header"
        :class="{ '--active': visibleDropdown }"
      >
        <span
          class="workspace-breadcrumb-dropdown__name"
          :class="{ '--last': isLastBreadcrumb }"
        >
          {{ selectedWorkspaceName }}
        </span>
        <BaseIcon
          name="chevron-down"
          class="workspace-breadcrumb-dropdown__icon"
          :class="{ '--rotated': visibleDropdown }"
        />
      </span>
      <span slot="dropdown-content" class="workspace-breadcrumb-dropdown__content">
        <div class="workspace-breadcrumb-dropdown__selector">
          <BaseSearch v-model="searchText" :placeholder="$t('search')" />
          <div class="workspace-breadcrumb-dropdown__items">
            <div v-if="workspaces.length === 0" class="workspace-breadcrumb-dropdown__empty">
              {{ $t('No workspaces available') }}
            </div>
            <div v-else-if="workspacesFilteredBySearchText.length === 0" class="workspace-breadcrumb-dropdown__empty">
              {{ $t('No workspaces match your search') }}
            </div>
            <BaseRadioButton
              v-else
              class="workspace-breadcrumb-dropdown__item"
              v-for="workspace in workspacesFilteredBySearchText"
              :key="workspace.id"
              :id="workspace.id"
              :name="workspace.id"
              :value="workspace.id"
              v-model="selectedWorkspaceId"
            >
              {{ workspace.name }}
              <span class="workspace-breadcrumb-dropdown__number">({{ workspace.numberOfDatasets || 0 }})</span>
            </BaseRadioButton>
          </div>
        </div>
      </span>
    </BaseDropdown>
  </div>
</template>

<script lang="ts">
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import "assets/icons/chevron-down";

export default {
  props: {
    workspaceId: {
      type: String,
      default: null,
    },
    isLastBreadcrumb: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      visibleDropdown: false,
      searchText: "",
    };
  },
  computed: {
    workspaceStore() {
      return useWorkspaces();
    },
    workspaces(): Workspace[] {
      return this.workspaceStore.get().workspaces;
    },
    selectedWorkspace(): Workspace | null {
      return this.workspaceStore.get().selectedWorkspace;
    },
    selectedWorkspaceName(): string {
      return this.selectedWorkspace?.name || this.$t('Select workspace');
    },
    selectedWorkspaceId: {
      get(): string | null {
        return this.selectedWorkspace?.id || null;
      },
      set(workspaceId: string | null) {
        const workspace = this.workspaces.find(w => w.id === workspaceId) || null;
        this.workspaceStore.saveSelectedWorkspace(workspace);
        this.onWorkspaceChange(workspace);
        this.visibleDropdown = false;
      }
    },
    workspacesFilteredBySearchText(): Workspace[] {
      return this.workspaces.filter((workspace) =>
        workspace.name.toLowerCase().includes(this.searchText.toLowerCase())
      );
    },
  },
  methods: {
    onToggleVisibility(value: boolean) {
      this.visibleDropdown = value;
    },
    onWorkspaceChange(workspace: Workspace | null) {
      // Emit breadcrumb link update event with workspace information
      this.$emit('workspace-change', {
        workspace,
        workspaceId: workspace?.id || null,
        workspaceName: workspace?.name || null,
        link: workspace ? {
          path: this.$route.path,
          query: { ...this.$route.query, workspace: workspace.name }
        } : {
          path: this.$route.path,
          query: { ...this.$route.query, workspace: undefined }
        }
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.workspace-breadcrumb-dropdown {
  display: inline-block;

  &__header {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--fg-lighter);
    text-decoration: none;
    outline: none;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: $border-radius-s;
    transition: all 0.2s ease;

    // Match breadcrumb item styling
    &:hover {
      background: var(--bg-opacity-4);
      color: var(--fg-secondary);
    }

    // Active state when dropdown is open
    &.--active {
      background: var(--bg-opacity-4);
      color: var(--fg-secondary);
    }
  }

  &__name {
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;

    // Match breadcrumb last item styling when this is the last breadcrumb
    &.--last {
      word-break: break-all;
      white-space: pre-line;
    }
  }

  &__icon {
    width: 12px;
    height: 12px;
    transition: transform 0.2s ease;
    fill: currentColor;
    opacity: 0.7;

    &.--rotated {
      transform: rotate(180deg);
    }
  }

  &__content {
    display: block;
    width: auto;
    max-width: 320px;
    min-width: 280px;
  }

  &__selector {
    padding: $base-space;
  }

  &__items {
    max-height: 200px;
    overflow: auto;
    margin-top: $base-space;
  }

  &__item {
    &.radio-button {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 6px $base-space;
      border-radius: $border-radius-s;
      transition: background-color 0.2s ease;

      &:hover {
        background: var(--bg-opacity-4);
      }
    }

    :deep(.radio-button__container) {
      background: none !important;
      border: 0 !important;
      flex: 1;
      min-width: 0;
    }

    :deep(label) {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
      min-width: 0;
    }

    &.radio-button :deep(.radio-button__container .svg-icon) {
      fill: var(--fg-cuaternary);
      min-width: 16px;
      flex-shrink: 0;
    }
  }

  &__number {
    @include font-size(12px);
    color: var(--fg-tertiary);
    margin-left: $base-space;
    flex-shrink: 0;
  }

  &__empty {
    padding: $base-space * 2;
    text-align: center;
    color: var(--fg-tertiary);
    @include font-size(12px);
    font-style: italic;
  }
}

// Override dropdown positioning for breadcrumb context
:deep(.dropdown__content) {
  right: 0;
  left: auto;
  z-index: 10; // Ensure it appears above other elements
}

// Responsive behavior for mobile
@include media("<=tablet") {
  .workspace-breadcrumb-dropdown {
    &__name {
      max-width: 150px;
    }

    &__content {
      min-width: 250px;
      max-width: 280px;
    }
  }
}
</style>