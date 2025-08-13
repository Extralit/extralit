<template>
  <div class="table-upload">
    <div class="table-upload__section-header">
      <h3 class="table-upload__section-title">Step 1: Upload Your Bibliography File</h3>
      <p class="table-upload__section-description">
        Import your reference list to begin.<br />
        We support .bib files exported from reference managers like Zotero, EndNote, or Mendeley, and .csv files with tabular data.
      </p>
    </div>

    <div class="table-upload__dropzone" :class="{
      'table-upload__dropzone--dragover': state.isDragging,
      'table-upload__dropzone--error': state.hasError,
      'table-upload__dropzone--success': state.uploaded,
    }" @drop="handleDrop" @dragover="handleDragOver" @dragleave="handleDragLeave"
      @click="triggerFileInput">
      <input ref="fileInput" type="file" accept=".bib,.bibtex,.csv" style="display: none"
        @change="handleFileSelect" />

      <div class="table-upload__dropzone-content">
        <BaseIcon :icon-name="getDropzoneIcon" class="table-upload__dropzone-icon" />
        <p class="table-upload__dropzone-text">
          {{ getDropzoneText }}
        </p>
        <p class="table-upload__dropzone-subtext">Supported formats: .bib, .bibtex, .csv</p>
      </div>
    </div>

    <!-- Success Display -->
    <div v-if="state.uploaded && !state.hasError" class="table-upload__upload-success">
      <BaseIcon icon-name="check" class="table-upload__upload-success-icon" />
      <span class="table-upload__upload-success-text">
        Successfully uploaded {{ strategy.data.fileName }} ({{ strategy.data.dataframeData ? strategy.data.dataframeData.data.length : 0 }} entries found)
      </span>
    </div>

    <!-- Error Display -->
    <div v-if="state.hasError" class="table-upload__error">
      <BaseIcon icon-name="danger" class="table-upload__error-icon" />
      <div class="table-upload__error-content">
        <h4>Bibliography Parsing Error</h4>
        <p>{{ state.errorMessage }}</p>
      </div>
    </div>

    <!-- CSV Column Selection -->
    <CsvColumnSelection
      v-if="strategy.showCsvColumnSelection"
      :csv-data="strategy.csvData"
      :csv-config="strategy.csvConfig"
      @config-updated="strategy.handleCsvConfigUpdate"
      @process-csv="processCsvWithConfig"
      @cancel="strategy.cancelCsvSelection"
    />
  </div>
</template>

<script lang="ts">
import { ref, defineComponent } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";
import CsvColumnSelection from "./CsvColumnSelection.vue";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";
import { createBibStrategy, useImportFileUploadViewModel } from "./useImportFileUploadViewModel";
import type { BibliographyData } from "./types";

export default defineComponent({
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
        type: 'bibliography'
      }),
    },
  },

  emits: ["update"],

  setup(props: any, { emit }: any) {
    const fileService = useResolve(FileParsingService);
    const strategy = createBibStrategy(fileService);
    
    const viewModel = useImportFileUploadViewModel(strategy, {
      enableDragDrop: true,
      acceptedExtensions: [".bib", ".bibtex", ".csv"]
    });

    // File input ref
    const fileInput = ref<HTMLInputElement | null>(null);

    // Initialize with existing data
    if (props.initialData && (props.initialData.fileName || (props.initialData.dataframeData && props.initialData.dataframeData.data.length > 0))) {
      viewModel.initialize(props.initialData);
    }

    // Handle CSV processing with config
    const processCsvWithConfig = async () => {
      try {
        await strategy.processCsvWithConfig();
        emitUpdate();
      } catch (error: any) {
        viewModel.showError(error.message);
      }
    };

    // File input handling
    const triggerFileInput = () => {
      fileInput.value?.click();
    };

    const handleFileSelect = async (event: Event) => {
      const target = event.target as HTMLInputElement;
      const files = target.files;
      if (files && files.length > 0) {
        await viewModel.selectFiles(Array.from(files));
        emitUpdate();
      }
    };

    // Emit update to parent
    const emitUpdate = () => {
      const payload = viewModel.emitPayload();
      emit("update", payload);
    };

    // Public methods for parent components
    const reset = () => {
      viewModel.reset();
      emitUpdate();
    };

    const initializeWithExistingData = () => {
      if (props.initialData && (props.initialData.fileName || (props.initialData.dataframeData && props.initialData.dataframeData.data.length > 0))) {
        viewModel.initialize(props.initialData);
        // Don't emit update when initializing with existing data to prevent loops
      }
    };

    return {
      ...viewModel,
      strategy,
      fileInput,
      processCsvWithConfig,
      triggerFileInput,
      handleFileSelect,
      reset,
      initializeWithExistingData,
    };
  },
});
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
