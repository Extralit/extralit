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
          {{ selectedDatasetName }}
        </span>
        <BaseIcon
          icon-name="chevron-down"
          class="breadcrumb-dropdown__icon"
          :class="{ '--rotated': visibleDropdown }"
        />
      </span>
      <span slot="dropdown-content" class="breadcrumb-dropdown__content">
        <div class="breadcrumb-dropdown__selector">
          <BaseSearch v-model="searchText" :placeholder="$t('searchDatasets')" />
          <div class="breadcrumb-dropdown__items">
            <div v-if="datasets.length === 0" class="breadcrumb-dropdown__empty">
              {{ $t('No datasets available') }}
            </div>
            <div v-else-if="datasetsFilteredBySearchText.length === 0" class="breadcrumb-dropdown__empty">
              {{ $t('No datasets match your search') }}
            </div>
            <template v-else>
              <BaseRadioButton
                class="breadcrumb-dropdown__item"
                v-for="dataset in datasetsFilteredBySearchText"
                :key="dataset.id"
                :id="dataset.id"
                :name="dataset.id"
                :value="dataset.id"
                :checked="selectedDatasetId === dataset.id"
                @change="onDatasetSelectionChange(dataset.id)"
              >
                {{ dataset.name }}
              </BaseRadioButton>
            </template>
          </div>
        </div>
      </span>
    </BaseDropdown>
  </div>
</template>

<script lang="ts">
import { useDatasets } from "~/v1/infrastructure/storage/DatasetsStorage";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { Dataset } from "~/v1/domain/entities/dataset/Dataset";
import "assets/icons/chevron-down";

export default {
  props: {
    datasetId: {
      type: String,
      default: null,
    },
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
    datasetStore() {
      return useDatasets();
    },
    workspaceStore() {
      return useWorkspaces();
    },
    allDatasets(): Dataset[] {
      return this.datasetStore.get().datasets;
    },
    selectedWorkspace() {
      return this.workspaceStore.get().selectedWorkspace;
    },
    // Filter datasets by selected workspace
    datasets(): Dataset[] {
      if (!this.selectedWorkspace) {
        return this.allDatasets;
      }
      return this.allDatasets.filter(dataset => dataset.workspaceId === this.selectedWorkspace.id);
    },
    selectedDataset(): Dataset | null {
      return this.datasets.find(d => d.id === this.datasetId) || null;
    },
    selectedDatasetName(): string {
      return this.selectedDataset?.name || this.$t('Select dataset');
    },
    selectedDatasetId: {
      get(): string | null {
        return this.datasetId;
      },
      set(datasetId: string | null) {
        const dataset = this.datasets.find(d => d.id === datasetId) || null;
        this.onDatasetChange(dataset);
        this.visibleDropdown = false;
      }
    },
    datasetsFilteredBySearchText(): Dataset[] {
      return this.datasets.filter((dataset) =>
        dataset.name.toLowerCase().includes(this.searchText.toLowerCase())
      );
    },
  },
  methods: {
    onToggleVisibility(value: boolean) {
      this.visibleDropdown = value;
    },
    onDatasetChange(dataset: Dataset | null) {
      if (dataset) {
        // Navigate to the selected dataset's annotation mode
        this.$router.push({
          path: `/dataset/${dataset.id}/annotation-mode`,
          query: {
            ...this.$route.query,
            workspace: this.selectedWorkspace?.name
          }
        });
      }
    },
    onDatasetSelectionChange(datasetId: string) {
      this.selectedDatasetId = datasetId;
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
    padding: $base-space / 2;
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