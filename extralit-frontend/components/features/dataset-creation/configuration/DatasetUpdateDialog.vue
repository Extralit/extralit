<template>
  <transition name="fade" appear>
    <dialog v-click-outside="closeDialog" class="dataset-update-dialog">
      <form class="dataset-update-dialog__content" @submit.prevent="updateDataset">
        <h1 class="dataset-update-dialog__title" v-text="$t('datasetCreation.updateDataset')" />

        <!-- Workspace Selection -->
        <div class="dataset-update-dialog__row">
          <label class="dataset-update-dialog__label" v-text="$t('datasetCreation.assignWorkspace')" />
          <template v-if="!workspaces.length">
            <span class="dataset-update-dialog__unique-workspace" v-text="$t('datasetCreation.none')" />
            <Validation :validations="[$t('datasetCreation.noWorkspaces')]" />
          </template>
          <span
            v-else-if="workspaces.length === 1"
            class="dataset-update-dialog__unique-workspace"
            v-text="selectedWorkspace?.name"
          />
          <DatasetConfigurationSelector
            v-else
            v-model="selectedWorkspace"
            :options="workspaces"
            @onValueChange="onWorkspaceChange"
          />
        </div>

        <!-- Target Dataset Selection -->
        <div class="dataset-update-dialog__row">
          <label class="dataset-update-dialog__label" v-text="$t('datasetCreation.datasetName')" />
          <template v-if="isLoadingCompatibleDatasets">
            <span class="dataset-update-dialog__loading" v-text="$t('datasetCreation.loadingCompatibleDatasets')" />
          </template>
          <template v-else-if="compatibleDatasets.length === 0">
            <span class="dataset-update-dialog__no-datasets" v-text="$t('datasetCreation.noCompatibleDatasets')" />
          </template>
          <DatasetConfigurationSelector
            v-else
            v-model="selectedTargetDataset"
            :options="compatibleDatasetOptions"
            :placeholder="$t('datasetCreation.selectDatasetPlaceholder')"
          />
        </div>

        <!-- Field Mapping Preview -->
        <div v-if="selectedTargetDataset" class="dataset-update-dialog__row">
          <label class="dataset-update-dialog__label" v-text="$t('datasetCreation.mapToColumn')" />
          <div class="dataset-update-dialog__mapping-preview">
            <div class="mapping-preview__header">
              <span v-text="$t('datasetCreation.sourceField')" />
              <span v-text="$t('datasetCreation.targetField')" />
            </div>
            <div v-for="field in schemaFields" :key="field.name" class="mapping-preview__row">
              <span class="mapping-preview__source">{{ field.name }}</span>
              <span class="mapping-preview__arrow">→</span>
              <span class="mapping-preview__target">
                {{ getMappedTargetField(field.name) || $t("datasetCreation.noMapping") }}
              </span>
            </div>
          </div>
        </div>

        <!-- Import Summary -->
        <div v-if="selectedTargetDataset" class="dataset-update-dialog__row">
          <div class="dataset-update-dialog__info">
            <p
              v-text="
                $t('datasetCreation.importSummary', {
                  records: totalRecords,
                  dataset: selectedTargetDataset.name,
                })
              "
            />
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="dataset-update-dialog__actions">
          <BaseButton
            :disabled="!selectedTargetDataset"
            :loading="isLoading"
            type="submit"
            class="primary"
            v-text="$t('datasetCreation.addRecords')"
          />
        </div>

        <Validation v-if="validationError" :validations="[validationError]" />
      </form>
    </dialog>
  </transition>
</template>

<script lang="ts">
import { useDatasetConfigurationNameAndWorkspace } from "./useDatasetConfigurationNameAndWorkspace";
import Validation from "../../annotation/settings/Validation.vue";
import { DatasetCreation } from "~/v1/domain/entities/hub/DatasetCreation";

export default {
  name: "DatasetUpdateDialog",
  components: { Validation },
  props: {
    dataset: {
      type: DatasetCreation,
      required: true,
    },
    isLoading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      selectedWorkspace: null,
      validationError: null,
    };
  },
  computed: {
    schemaFields() {
      return this.dataset?.selectedSubset?.fields || [];
    },
    columnNames() {
      return this.schemaFields ? this.schemaFields.map((field) => field.name) : [];
    },
    totalRecords() {
      // This would come from the dataset or import metadata
      return (this.dataset?.selectedSubset as { totalRecords?: number })?.totalRecords || 0;
    },
    compatibleDatasetOptions() {
      return this.compatibleDatasets.map((dataset) => ({
        id: dataset.id,
        name: dataset.name,
        value: dataset,
      }));
    },
    firstWorkspace() {
      if (this.workspaces.length && !this.selectedWorkspace) {
        return this.workspaces[0];
      }
    },
  },
  watch: {
    selectedWorkspace: {
      async handler(newWorkspace) {
        if (newWorkspace && this.schemaFields.length > 0) {
          await this.loadCompatibleDatasetsForWorkspace();
        }
      },
    },
    firstWorkspace: {
      handler(value) {
        if (value && !this.selectedWorkspace) {
          this.selectedWorkspace = this.firstWorkspace;
        }
      },
      deep: true,
    },
  },
  mounted() {
    // Auto-select workspace if only one available or set first workspace
    if (this.workspaces.length === 1) {
      this.selectedWorkspace = this.workspaces[0];
    } else if (this.firstWorkspace) {
      this.selectedWorkspace = this.firstWorkspace;
    }
  },
  methods: {
    closeDialog() {
      this.$emit("close-dialog");
    },
    async updateDataset() {
      if (!this.selectedTargetDataset) {
        this.validationError = this.$t("datasetCreation.selectDatasetRequired");
        return;
      }

      // Convert BackendDataset to target dataset info with workspace
      const targetDataset = this.convertBackendDatasetToTargetInfo(this.selectedTargetDataset, this.selectedWorkspace);

      if (!targetDataset) {
        this.validationError = "Missing target dataset or workspace information";
        return;
      }

      this.$emit("update-dataset", {
        targetDataset,
        source: this.dataset,
      });
    },
    async onWorkspaceChange() {
      // Reset dataset selection when workspace changes
      this.selectedTargetDataset = null;
      if (this.selectedWorkspace) {
        await this.loadCompatibleDatasetsForWorkspace();
      }
    },
    async loadCompatibleDatasetsForWorkspace() {
      if (!this.selectedWorkspace || !this.columnNames || !this.columnNames.length) return;

      await this.loadCompatibleDatasets(this.columnNames, this.selectedWorkspace.id);
    },
    getMappedTargetField(sourceFieldName) {
      // This would be enhanced to show actual field mapping
      // For now, return the source field name if it exists in target
      return sourceFieldName;
    },
  },
  setup() {
    return useDatasetConfigurationNameAndWorkspace();
  },
};
</script>

<style lang="scss" scoped>
.dataset-update-dialog {
  position: absolute;
  right: 0;
  left: 0;
  width: 100%;
  bottom: -4px;
  display: block;
  margin-left: auto;
  padding: 0;
  border: 1px solid var(--bg-opacity-10);
  border-radius: $border-radius-m;
  box-shadow: $shadow;
  z-index: 1;

  &__content {
    display: flex;
    flex-direction: column;
    gap: $base-space;
    padding: $base-space * 2;
  }

  &__title {
    font-weight: 500;
    @include font-size(16px);
    margin: 0 0 $base-space 0;
  }

  &__row {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__label {
    font-weight: 400;
    @include font-size(14px);
  }

  &__unique-workspace {
    height: $base-space * 4;
    line-height: $base-space * 4;
    padding: 0 $base-space;
    background: var(--bg-opacity-4);
    border: none;
    border-radius: $border-radius;
    color: var(--fg-secondary);
    @include font-size(12px);
    user-select: none;
  }

  &__loading,
  &__no-datasets {
    padding: $base-space;
    background: var(--bg-accent-grey-1);
    border-radius: $border-radius-s;
    color: var(--fg-secondary);
    font-style: italic;
  }

  &__mapping-preview {
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-s;
    overflow: hidden;

    .mapping-preview__header {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: $base-space;
      background: var(--bg-accent-grey-1);
      padding: $base-space;
      font-weight: 500;
      border-bottom: 1px solid var(--bg-opacity-6);
    }

    .mapping-preview__row {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: $base-space;
      padding: $base-space;
      border-bottom: 1px solid var(--bg-opacity-6);
      align-items: center;

      &:last-child {
        border-bottom: none;
      }
    }

    .mapping-preview__source {
      font-family: monospace;
      color: var(--fg-primary);
    }

    .mapping-preview__arrow {
      color: var(--fg-secondary);
      text-align: center;
    }

    .mapping-preview__target {
      font-family: monospace;
      color: var(--color-brand-primary);

      &:empty::before {
        content: attr(data-placeholder);
        color: var(--fg-secondary);
        font-style: italic;
      }
    }
  }

  &__info {
    background: var(--bg-accent-info);
    border: 1px solid var(--color-info);
    border-radius: $border-radius-s;
    padding: $base-space * 2;

    p {
      margin: 0;
      color: var(--fg-primary);
    }
  }

  &__actions {
    display: flex;
    gap: $base-space;

    .button {
      width: 100%;
      justify-content: center;
    }
  }

  &__info {
    font-weight: 400;
    @include font-size(11px);
    @include line-height(14px);
    color: var(--fg-tertiary);
    margin-bottom: 0;

    background: var(--bg-accent-info);
    border: 1px solid var(--color-info);
    border-radius: $border-radius-s;
    padding: $base-space * 2;

    p {
      margin: 0;
      color: var(--fg-primary);
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
