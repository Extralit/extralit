<template>
  <div class="breadcrumb-dropdown">
    <BaseDropdown :visible="visibleDropdown" @visibility="onToggleVisibility">
      <span
        slot="dropdown-header"
        class="breadcrumb-dropdown__header"
      >
        <span
          class="breadcrumb-dropdown__name"
          :class="{ '--last': isLastBreadcrumb }"
        >
          {{ selectedWorkspaceName }}
        </span>
        <BaseIcon
          icon-name="chevron-down"
          class="breadcrumb-dropdown__icon"
          :class="{ '--rotated': visibleDropdown }"
        />
      </span>
      <span slot="dropdown-content" class="breadcrumb-dropdown__content">
        <div class="breadcrumb-dropdown__selector">
          <BaseSearch v-model="searchText" :placeholder="$t('search')" />
          <div class="breadcrumb-dropdown__items">
            <div v-if="workspaces.length === 0" class="breadcrumb-dropdown__empty">
              {{ $t('No workspaces available') }}
            </div>
            <div v-else-if="workspacesFilteredBySearchText.length === 0" class="breadcrumb-dropdown__empty">
              {{ $t('No workspaces match your search') }}
            </div>
            <template v-else>
              <BaseRadioButton
                class="breadcrumb-dropdown__item"
                v-for="workspace in workspacesFilteredBySearchText"
                :key="workspace.id"
                :id="workspace.id"
                :name="workspace.id"
                :value="workspace.id"
                :checked="selectedWorkspaceId === workspace.id"
                @change="onWorkspaceSelectionChange(workspace.id)"
              >
                {{ workspace.name }}
              </BaseRadioButton>
            </template>
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
    onWorkspaceSelectionChange(workspaceId: string) {
      this.selectedWorkspaceId = workspaceId;
    }
  },
};
</script>

<style lang="scss" scoped>
.breadcrumb-dropdown {
  position: relative;

  &__header {
    display: flex;
    align-items: center;
    padding: $base-space / 2;
    color: var(--fg-lighter);
    cursor: pointer;
    border-radius: $border-radius-s;
    transition: all 0.2s ease;

    &:hover {
      background: var(--bg-opacity-20);
    }
  }

  &__name {
    font-weight: 600;
    white-space: nowrap;
    line-height: 1;

    &.--last {
      word-break: break-all;
    }
  }

  &__icon {
    width: 12px;
    height: 12px;
    margin-left: 4px;
    transition: transform 0.2s ease;
    fill: currentColor;
    opacity: 0.8;

    &.--rotated {
      transform: rotate(180deg);
    }
  }

  &__content {
    display: block;
    margin-top: 0;
  }

  &__selector {
    padding: $base-space;
  }

  &__items {
    padding: 0;
  }

  &__item {
    &.radio-button {
      display: flex;
      align-items: center;
      padding: $base-space;
      border-radius: $border-radius-s;
      transition: background-color 0.2s ease;

      &:hover {
        background: var(--bg-opacity-20);
      }
    }

    :deep(.radio-button__container) {
      display: none !important;
    }

    :deep(label) {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
      margin: 0;
      padding: 0;
    }

    &.radio-button :deep(.radio-button__container .svg-icon) {
      fill: var(--fg-cuaternary);
    }
  }

  &__number {
    @include font-size(12px);
    color: var(--fg-tertiary);
    margin-left: $base-space;
    flex-shrink: 0;
  }

  &__empty {
    text-align: center;
    color: var(--fg-tertiary);
    @include font-size(12px);
    font-style: italic;
  }
}

:deep(.dropdown__content) {
  right: auto;
  left: 0;
  z-index: 10;
  margin-top: 0;
  min-width: 120px;
  border: 1px solid var(--border-field);
  box-shadow: var(--shadow-200);
  border-radius: $border-radius-s;
}

:deep(.dropdown) {
  margin: 0;
  padding: 0;
}

:deep(.dropdown__wrapper) {
  position: absolute;
  top: 100%;
  left: 0;
}

:deep(.base-search) {
  margin: 0;

  .base-search__input {
    padding: $base-space / 2;
    border-radius: $border-radius-s;
    border: 1px solid var(--border-field);
    background: var(--bg-field);
    color: var(--fg-primary);

    &::placeholder {
      color: var(--fg-tertiary);
    }
  }
}

:deep(.radio-button) {
  margin: 0 0 2px 0;
  padding: 0;
  gap: 0;

  .radio-button__label {
    width: 100%;
    flex: 1;
  }
}

</style>