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
      'table-upload__dropzone--dragover': viewModel.state.isDragging,
      'table-upload__dropzone--error': viewModel.state.hasError,
      'table-upload__dropzone--success': viewModel.state.uploaded,
    }" @drop="viewModel.handleDrop" @dragover="viewModel.handleDragOver" @dragleave="viewModel.handleDragLeave"
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
    <div v-if="viewModel.state.uploaded && !viewModel.state.hasError" class="table-upload__upload-success">
      <BaseIcon icon-name="check" class="table-upload__upload-success-icon" />
      <span class="table-upload__upload-success-text">
        Successfully uploaded {{ viewModel.state.data?.fileName }} ({{ viewModel.state.data?.dataframeData?.data?.length || 0 }} entries found)
      </span>
    </div>

    <!-- Error Display -->
    <div v-if="viewModel.state.hasError" class="table-upload__error">
      <BaseIcon icon-name="danger" class="table-upload__error-icon" />
      <div class="table-upload__error-content">
        <h4>Bibliography Parsing Error</h4>
        <p>{{ viewModel.state.errorMessage }}</p>
      </div>
    </div>

    <!-- CSV Column Selection -->
    <CsvColumnSelection
      v-if="csvData.showColumnSelection"
      :csv-data="csvData"
      :csv-config="csvData.config"
      @config-updated="handleCsvConfigUpdate"
      @process-csv="processCsvWithConfig"
      @cancel="cancelCsvSelection"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from '@nuxtjs/composition-api';
import { useResolve } from "ts-injecty";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";
import CsvColumnSelection from "./CsvColumnSelection.vue";
import { useImportFileUploadViewModel, createBibStrategy } from "./useImportFileUploadViewModel";
import type { BibliographyData } from "./types";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";

// Props and emits
interface Props {
  initialData?: BibliographyData;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  update: [data: any];
}>();

// Services
const fileService = useResolve(FileParsingService);

// CSV column selection state (managed by strategy but exposed for component)
const csvData = ref({
  rawData: null,
  columns: [] as string[],
  previewRows: [] as any[],
  showColumnSelection: false,
  config: {
    referenceColumn: '',
    filesColumn: '',
  } as CSVConfig,
});

// Create bibliography strategy with CSV callbacks
const strategy = createBibStrategy({
  fileParsingService: fileService,
  onCsvConfigRequired: (previewData) => {
    // Update local CSV state when config is required
    csvData.value = {
      ...csvData.value,
      rawData: previewData.rawData,
      columns: previewData.columns,
      previewRows: previewData.previewRows,
      showColumnSelection: true,
    };
  },
  onCsvConfigComplete: () => {
    csvData.value.showColumnSelection = false;
  },
});

// Create view model
const viewModel = useImportFileUploadViewModel(strategy, {
  onUpdate: (payload) => {
    if (payload) {
      emit('update', {
        isValid: viewModel.isValid(),
        fileName: payload.fileName,
        dataframeData: payload.dataframeData,
        rawContent: payload.rawContent,
      });
    }
  },
});

// File input ref
const fileInput = ref<HTMLInputElement | null>(null);

// Computed properties
const getDropzoneIcon = computed(() => {
  if (viewModel.state.hasError) return "danger";
  if (viewModel.state.uploaded) return "check";
  return "document";
});

const getDropzoneText = computed(() => {
  if (viewModel.state.hasError) return "Error parsing bibliography file";
  if (viewModel.state.uploaded) return "Upload BibTeX File";
  return "Upload BibTeX File";
});

// Methods
function triggerFileInput(): void {
  fileInput.value?.click();
}

function handleFileSelect(event: Event): void {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  viewModel.selectFiles(files);
}

async function processCsvWithConfig(): Promise<void> {
  try {
    const dataframeData = await (strategy as any).processCsvWithConfig(csvData.value.config);
    
    // Update the viewModel state with completed CSV processing
    viewModel.state.data = {
      ...viewModel.state.data,
      dataframeData,
    };
    viewModel.state.uploaded = true;
    
    // Emit update
    emit('update', {
      isValid: viewModel.isValid(),
      fileName: viewModel.state.data.fileName,
      dataframeData,
      rawContent: viewModel.state.data.rawContent,
    });
  } catch (error: any) {
    viewModel.showError(`Failed to process CSV data: ${error.message}`);
  }
}

function handleCsvConfigUpdate(config: CSVConfig): void {
  csvData.value.config = config;
}

function cancelCsvSelection(): void {
  csvData.value.showColumnSelection = false;
  viewModel.reset();
}

// Initialize with existing data
watch(() => props.initialData, (newData) => {
  if (newData && (newData.fileName || newData?.dataframeData?.data?.length > 0)) {
    viewModel.initialize(newData);
  }
}, { deep: true, immediate: true });

// Expose reset method for parent
defineExpose({
  reset: viewModel.reset,
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
