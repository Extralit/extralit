<template>
  <div class="table-upload">
    <div class="table-upload__section-header">
      <h3 class="table-upload__section-title">Bibliography / Metadata (Optional)</h3>
      <p class="table-upload__section-description">
        Have a reference file from Zotero, EndNote, or Mendeley? Upload it to auto-match metadata. If not, you can edit the table in the next step.
      </p>
    </div>

    <div class="table-upload__dropzone" :class="{
      'table-upload__dropzone--dragover': dragOver,
      'table-upload__dropzone--error': hasError,
      'table-upload__dropzone--success': uploaded,
    }" @drop="handleDrop" @dragover="handleDragOver" @dragleave="handleDragLeave"
      @click="triggerFileInput">
      <input ref="fileInput" type="file" accept=".bib,.bibtex,.csv" style="display: none"
        @change="handleFileSelect" />

      <div class="table-upload__dropzone-content">
        <BaseIcon :icon-name="getDropzoneIcon" class="table-upload__dropzone-icon" />
        <p class="table-upload__dropzone-text">
          {{ getDropzoneText }}
        </p>
        <p class="table-upload__dropzone-subtext">Supports .bib, .bibtex, .csv</p>
      </div>
    </div>

    <!-- Success Display -->
    <div v-if="uploaded && !hasError" class="table-upload__upload-success">
      <span class="table-upload__upload-success-text">
        Successfully uploaded {{ data.fileName }} ({{ data.dataframeData ? data.dataframeData.data.length : 0 }} entries found)
      </span>
    </div>

    <!-- Error Display -->
    <div v-if="hasError" class="table-upload__error">
      <BaseIcon icon-name="danger" class="table-upload__error-icon" />
      <div class="table-upload__error-content">
        <h4>Bibliography Parsing Error</h4>
        <p>{{ errorMessage }}</p>
      </div>
    </div>

    <!-- CSV Column Selection -->
    <CsvColumnSelection
      v-if="showCsvColumnSelection"
      :csv-data="csvData"
      :csv-config="csvConfig"
      @config-updated="handleCsvConfigUpdate"
      @process-csv="processCsvWithConfig"
      @cancel="cancelCsvSelection"
    />
  </div>
</template>

<script lang="ts">
import CsvColumnSelection from "./CsvColumnSelection.vue";
import { useTableUploadLogic } from "./useTableUploadLogic";
import type { BibliographyData } from "./types";

export default {
  name: "TableUpload",

  components: {
    CsvColumnSelection,
  },

  props: {
    initialData: {
      type: Object as () => BibliographyData,
      default: () => ({
        fileName: "",
        dataframeData: null,
        rawContent: "",
      }),
    },
  },

  emits: ["update"],

  setup(props: any, { emit }: any) {
    return useTableUploadLogic(props, emit);
  },
};
</script>

<style lang="scss" scoped>
.table-upload {
  display: flex;
  flex-direction: column;
  gap: $base-space * 2;
}

.table-upload__section-header {
  margin-bottom: $base-space * 2;
}

.table-upload__section-title {
  font-size: 1.2rem;
  font-weight: 600;
  margin-bottom: $base-space;
  color: var(--fg-primary);
}

.table-upload__section-description {
  color: var(--fg-secondary);
  font-size: 0.9rem;
  margin-bottom: 0;
  line-height: 1.4;
}

.table-upload__dropzone {
  border: 2px dashed var(--border-field);
  border-radius: $border-radius-m;
  padding: $base-space * 4 $base-space * 3;
  text-align: center;
  cursor: pointer;
  transition: $swift-ease-out;
  background: var(--bg-accent-grey-1);

  &:hover {
    border-color: var(--bg-action);
    background: var(--bg-accent-grey-2);
  }

  &--dragover {
    border-color: var(--bg-action);
    background: var(--bg-accent-grey-2);
    transform: scale(1.02);
  }

  &--error {
    border-color: var(--color-danger);
    background: var(--bg-banner-error);
  }

  &--success {
    border-color: var(--color-success);
    background: var(--bg-solid-grey-2);
  }
}

.table-upload__dropzone-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $base-space;
}

.table-upload__dropzone-icon {
  font-size: 3rem;
  color: var(--fg-secondary);
}

.table-upload__dropzone-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: var(--fg-primary);
  margin: 0;
}

.table-upload__dropzone-subtext {
  font-size: 0.9rem;
  color: var(--fg-secondary);
  margin: 0;
}

.table-upload__upload-success {
  display: flex;
  align-items: center;
  gap: $base-space;
  padding: $base-space;
  background: var(--bg-solid-grey-2);
  border: 1px solid var(--color-success);
  border-radius: $border-radius;
  margin-top: $base-space;
}

.table-upload__upload-success-icon {
  color: var(--color-success);
  font-size: 1rem;
  flex-shrink: 0;
}

.table-upload__upload-success-text {
  color: var(--fg-primary);
  font-size: 0.9rem;
  font-weight: 500;
}

.table-upload__error {
  display: flex;
  align-items: flex-start;
  gap: $base-space;
  padding: $base-space * 2;
  background: var(--bg-banner-error);
  border: 1px solid var(--color-danger);
  border-radius: $border-radius;
}

.table-upload__error-icon {
  color: var(--color-danger);
  font-size: 1.2rem;
  margin-top: 0.1rem;
}

.table-upload__error-content h4 {
  margin: 0 0 $base-space 0;
  color: var(--color-danger);
  font-size: 1rem;
}

.table-upload__error-content p {
  margin: 0;
  color: var(--fg-primary);
}
</style>
