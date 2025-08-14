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
        <p class="table-upload__dropzone-subtext">Supported formats: .bib, .bibtex, .csv</p>
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
import { useResolve } from "ts-injecty";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";
import CsvColumnSelection from "./CsvColumnSelection.vue";
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/document";
import { TableData } from "~/v1/domain/entities/table/TableData";

interface BibliographyData {
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
}

interface CsvData {
  rawData: any;
  columns: string[];
  previewRows: any[];
}

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

  setup() {
    const fileService = useResolve(FileParsingService);
    return { fileService };
  },

  data() {
    return {
      dragOver: false,
      uploaded: false,
      hasError: false,
      errorMessage: "",
      data: {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      } as BibliographyData,

      // CSV parsing state
      showCsvColumnSelection: false,
      csvData: {
        rawData: null,
        columns: [],
        previewRows: [],
      } as CsvData,
      csvConfig: {
        referenceColumn: "",
        filesColumn: "",
      } as CSVConfig,
    };
  },

  mounted() {
    this.initializeWithExistingData();
  },

  computed: {
    getDropzoneIcon(): string {
      if (this.hasError) return "danger";
      if (this.uploaded) return "check";
      return "document";
    },

    getDropzoneText(): string {
      if (this.hasError) return "Error parsing bibliography file";
      if (this.uploaded) return "Upload BibTeX File";
      return "Upload BibTeX File";
    },
  },

  watch: {
    initialData: {
      handler(newData: BibliographyData) {
        if (newData && (newData.fileName || newData?.dataframeData?.data?.length > 0)) {
          this.initializeWithExistingData();
        }
      },
      deep: true,
      immediate: true,
    },
  },

  methods: {
    triggerFileInput(): void {
      (this.$refs.fileInput as HTMLInputElement).click();
    },

    handleDragOver(event: DragEvent): void {
      event.preventDefault();
      this.dragOver = true;
    },

    handleDragLeave(): void {
      this.dragOver = false;
    },

    handleDrop(event: DragEvent): void {
      event.preventDefault();
      this.dragOver = false;

      const files = event.dataTransfer?.files;
      if (files && files.length > 0) {
        this.processFile(files[0]);
      }
    },

    handleFileSelect(event: Event): void {
      const target = event.target as HTMLInputElement;
      const files = target.files;
      if (files && files.length > 0) {
        this.processFile(files[0]);
      }
    },

    async processFile(file: File): Promise<void> {
      // Reset state
      this.hasError = false;
      this.errorMessage = "";
      this.data = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };

      // Reset CSV state
      this.showCsvColumnSelection = false;
      this.csvData = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Validate file type
      if (!this.fileService.isValidFileType(file, [".bib", ".bibtex", ".csv"])) {
        this.showError("Invalid file type. Please upload a .bib, .bibtex, or .csv file.");
        return;
      }

      this.data.fileName = file.name;

      try {
        // Read file content
        const content = await this.fileService.readFileContent(file);
        this.data.rawContent = content;

        if (this.isCsvFile(file)) {
          // Handle CSV file
          await this.parseCsvContent(content);
        } else if (this.isBibTexFile(file)) {
          // Handle BibTeX file
          this.data.dataframeData = await this.fileService.parseBibTeX(content);

          if (this.data.dataframeData && this.data.dataframeData.data.length > 0) {
            this.uploaded = true;
            this.emitUpdate();
          } else {
            this.showError("No valid BibTeX entries found in the file.");
          }
        }
      } catch (error: any) {
        this.showError(`Failed to process file: ${error.message}`);
      }
    },

    isCsvFile(file: File): boolean {
      return file.name.toLowerCase().endsWith(".csv");
    },

    isBibTexFile(file: File): boolean {
      const fileName = file.name.toLowerCase();
      return fileName.endsWith(".bib") || fileName.endsWith(".bibtex");
    },

    async parseCsvContent(content: string): Promise<void> {
      try {
        const previewData = await this.fileService.parseCSVForPreview(content);

        // Store CSV data for column selection
        this.csvData = {
          rawData: previewData.rawData,
          columns: previewData.columns,
          previewRows: previewData.previewRows,
        };

        // Show column selection UI
        this.showCsvColumnSelection = true;

      } catch (error: any) {
        throw new Error(`CSV parsing failed: ${error.message}`);
      }
    },

    async processCsvWithConfig(): Promise<void> {
      try {
        if (!this.csvConfig.referenceColumn) {
          this.showError("Please select a reference column to continue.");
          return;
        }

        if (!this.csvData.rawData || this.csvData.rawData.length === 0) {
          this.showError("No CSV data available. Please upload a file first.");
          return;
        }

        this.data.dataframeData = await this.fileService.parseCSVWithConfig(this.csvData.rawData, this.csvConfig);

        // Hide column selection and mark as uploaded
        this.showCsvColumnSelection = false;
        this.uploaded = true;
        this.emitUpdate();

      } catch (error: any) {
        this.showError(`Failed to process CSV data: ${error.message}`);
      }
    },

    handleCsvConfigUpdate(config: CSVConfig): void {
      this.csvConfig = config;
    },

    cancelCsvSelection(): void {
      // Reset CSV state and clear upload
      this.showCsvColumnSelection = false;
      this.csvData = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Reset data
      this.data = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };
      this.uploaded = false;
      this.hasError = false;
      this.errorMessage = "";
    },

    showError(message: string): void {
      this.hasError = true;
      this.errorMessage = message;
      this.uploaded = false;
    },

    initializeWithExistingData(): void {
      if (this.initialData && (this.initialData.fileName || (this.initialData.dataframeData && this.initialData.dataframeData.data.length > 0))) {
        this.data = {
          fileName: this.initialData.fileName || "",
          dataframeData: this.initialData.dataframeData || null,
          rawContent: this.initialData.rawContent || "",
        };
        this.uploaded = this.data.dataframeData && this.data.dataframeData.data.length > 0;
        this.hasError = false;
        this.errorMessage = "";
        this.showCsvColumnSelection = false;
        // Don't emit update when initializing with existing data to prevent loops
        // The parent component already has this data
      }
    },

    emitUpdate(): void {
      this.$emit("update", {
        isValid: this.uploaded && !this.hasError && this.data.dataframeData && this.data.dataframeData.data.length > 0,
        fileName: this.data.fileName,
        dataframeData: this.data.dataframeData,
        rawContent: this.data.rawContent,
      });
    },

    reset(): void {
      this.dragOver = false;
      this.uploaded = false;
      this.hasError = false;
      this.errorMessage = "";
      this.data = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };
      this.showCsvColumnSelection = false;
      this.csvData = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      this.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };
    },
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
