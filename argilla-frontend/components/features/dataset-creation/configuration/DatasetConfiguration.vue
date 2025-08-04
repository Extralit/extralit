<template>
  <div class="dataset-config">
    <HorizontalResizable
      :min-height-percent="30"
      :top-percent-height="34"
      :id="`dataset-config-r-h-rz`"
      class="wrapper"
    >
      <template #up>
        <VerticalResizable :id="`dataset-config-left-t-v-rz`" :left-percent-width="64">
          <template #left>
            <div class="dataset-config__fields">
              <Record
                v-if="firstRecord"
                :key="JSON.stringify(dataset.mappedFields)"
                :recordCriteria="{
                  committed: {
                    searchText: {
                      value: {
                        text: '',
                      },
                    },
                  },
                }"
                :record="{
                  fields: dataset.createFields(firstRecord),
                }"
              />
            </div>
          </template>
          <template #right>
            <div class="dataset-config__questions-wrapper">
              <p
                v-if="!dataset.questions.length"
                class="dataset-config__empty-questions"
                v-text="$t('datasetCreation.yourQuestions')"
              />

              <QuestionsComponent
                v-else
                class="dataset-config__questions"
                :visible-shortcuts="false"
                :questions="dataset.questions"
              />
            </div>
          </template>
        </VerticalResizable>
      </template>
      <template #down>
        <VerticalResizable class="dataset-config__down" :id="`dataset-preview-t-v-rz`" :left-percent-width="36">
          <template #left>
            <div class="dataset-config__preview">
              <!-- HuggingFace Hub preview -->
              <iframe
                v-if="dataSource === 'hub' && !!dataset.repoId"
                :src="`https://huggingface.co/datasets/${dataset.repoId}/embed/viewer/ParaphraseRC/train`"
                frameborder="0"
                width="100%"
                height="100%"
              ></iframe>

              <!-- ImportHistory data preview -->
              <ImportHistoryDataPreview
                v-else-if="dataSource === 'import' && importData"
                :import-history-details="importData"
                :loading="isLoadingImportData"
                :error="importDataError"
                @retry="$emit('retry-import-data')"
                @row-selected="handleImportRowSelected"
                @field-selected="handleImportFieldSelected"
              />

              <!-- Fallback for missing data -->
              <div v-else class="dataset-config__preview-placeholder">
                <BaseIcon icon-name="document" />
                <p>No preview data available</p>
              </div>
            </div>
          </template>
          <template #right>
            <div class="dataset-config__configuration">
              <DatasetConfigurationForm :dataset="dataset" @change-subset="$emit('change-subset', $event)" />
            </div>
          </template>
        </VerticalResizable>
      </template>
    </HorizontalResizable>
  </div>
</template>

<script>
import "assets/icons/document";
import { useDatasetConfiguration } from "./useDatasetConfiguration";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

export default {
  props: {
    dataset: {
      type: Object,
      required: true,
    },
    dataSource: {
      type: String,
      default: "hub",
      validator: (value) => ["hub", "import"].includes(value),
    },
    importData: {
      type: ImportHistoryDetails,
      default: null,
    },
    isLoadingImportData: {
      type: Boolean,
      default: false,
    },
    importDataError: {
      type: String,
      default: null,
    },
  },
  emits: ["change-subset", "retry-import-data", "import-row-selected", "import-field-selected"],
  mounted() {
    this.getFirstRecord(this.dataset, this.dataSource, this.importData);
  },
  watch: {
    dataset: {
      handler(newDataset) {
        this.getFirstRecord(newDataset, this.dataSource, this.importData);
      },
      deep: true,
    },
    importData: {
      handler(newImportData) {
        if (this.dataSource === "import" && newImportData) {
          this.getFirstRecord(this.dataset, this.dataSource, newImportData);
        }
      },
      deep: true,
    },
    dataSource: {
      handler(newDataSource) {
        this.getFirstRecord(this.dataset, newDataSource, this.importData);
      },
    },
  },
  methods: {
    handleImportRowSelected(rowData) {
      this.$emit("import-row-selected", rowData);
    },
    handleImportFieldSelected(fieldData) {
      this.$emit("import-field-selected", fieldData);
    },
  },
  setup() {
    return useDatasetConfiguration();
  },
};
</script>

<style scoped lang="scss">
.wrapper {
  @include media("<desktop") {
    overflow: auto;
  }
}
.dataset-config {
  height: 100%;
  min-height: 0;
  &__fields {
    width: 100%;
    height: 100%;
    padding: $base-space * 2;
    :deep(.record) {
      border-style: dashed;
      border-color: var(--bg-opacity-10);
    }
  }
  &__down {
    display: flex;
    height: 100%;
    width: 100%;
    :deep(.resizable-v__left) {
      background: var(--bg-accent-grey-1);
    }
  }
  &__preview {
    align-items: flex-start;
    justify-items: center;
    padding: $base-space * 2;
    width: 40vw;
    height: 100%;
    overflow: auto;
    @include media("<tablet") {
      width: 100%;
    }
  }
  &__empty-questions {
    width: 100%;
    text-align: center;
    padding: $base-space * 4;
    color: var(--fg-secondary);
    background-color: var(--bg-accent-grey-1);
    border: 1px dashed var(--bg-opacity-10);
    border-radius: $border-radius-m;
    margin: 0;
    @include font-size(16px);
  }
  &__dataset-preview {
    color: var(--fg-secondary);
    @include font-size(16px);
  }
  &__questions-wrapper {
    width: 100%;
    height: 100%;
    padding: $base-space * 2;
    overflow: auto;
  }
  &__questions {
    background: var(--bg-form);
    border: 1px solid var(--bg-opacity-6);
    border-radius: $border-radius-m;
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
    overflow: auto;
    padding: $base-space * 2;
    position: relative;
    scroll-behavior: smooth;
  }
  &__configuration {
    width: 100%;
    height: 100%;
  }
  &__preview-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--fg-secondary);
    gap: $base-space * 2;

    p {
      margin: 0;
      font-size: 0.9rem;
    }
  }
}
</style>
