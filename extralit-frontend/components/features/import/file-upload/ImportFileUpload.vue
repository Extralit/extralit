<template>
  <div class="import-file-upload">
    <div class="import-file-upload__header">
      <h1 class="import-file-upload__title">Upload References and PDF Files</h1>
      <p class="import-file-upload__description">Upload your BibTeX file and PDF folder to import your references</p>
    </div>

    <div class="import-file-upload__content">
      <div class="import-file-upload__main">
        <!-- Table Upload Section -->
        <TableUpload :initial-data="bibData" @update="handleBibUpdate" />

        <!-- PDF Upload Section -->
        <PdfUpload :initial-data="pdfData" :bibliography-entries="bibData.dataframeData" @update="handlePdfUpdate" />
      </div>

      <!-- Summary Sidebar -->
      <ImportSummarySidebar :bib-data="bibData" :pdf-data="pdfData" />
    </div>
  </div>
</template>

<script lang="ts">
import TableUpload from "./TableUpload.vue";
import PdfUpload from "./PdfUpload.vue";
import ImportSummarySidebar from "./ImportSummarySidebar.vue";

type ComponentData = {
  isInitializing: boolean;
  bibData: {
    fileName: string;
    dataframeData: any;
    rawContent: string;
  };
  pdfData: {
    matchedFiles: any[];
    unmatchedFiles: any[];
    totalFiles: number;
  };
};

export default {
  name: "ImportFileUpload",

  components: {
    TableUpload,
    PdfUpload,
    ImportSummarySidebar,
  } as any,

  props: {
    // Props to receive existing data when navigating back to this step
    initialBibData: {
      type: Object,
      default: () => ({
        fileName: "",
        dataframeData: null,
        rawContent: "",
      }),
    },
    initialPdfData: {
      type: Object,
      default: () => ({
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      }),
    },
  },

  data(): ComponentData {
    return {
      // Internal flag to prevent recursive updates during initialization
      isInitializing: false,

      // Bibliography data
      bibData: {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      },

      // PDF data
      pdfData: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      },
    };
  },

  computed: {
    isValid(): boolean {
      return (
        this.bibData.dataframeData && this.bibData.dataframeData.data.length > 0 &&
        this.pdfData.matchedFiles.length > 0
      );
    },
  },

  watch: {
    initialBibData: {
      handler(newData: any, oldData: any) {
        // Only initialize if data has actually changed and we're not already initializing
        if (!this.isInitializing && newData && (newData.fileName || (newData.dataframeData && newData.dataframeData.data.length > 0))) {
          // Check if the data is actually different to avoid unnecessary updates
          const hasChanged = !oldData ||
            newData.fileName !== oldData.fileName ||
            (newData.dataframeData?.data?.length || 0) !== (oldData.dataframeData?.data?.length || 0);

          if (hasChanged) {
            this.initializeWithExistingData();
          }
        }
      },
      deep: true,
      immediate: true,
    },

    initialPdfData: {
      handler(newData: any, oldData: any) {
        // Only initialize if data has actually changed and we're not already initializing
        if (!this.isInitializing && newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0)) {
          // Check if the data is actually different to avoid unnecessary updates
          const hasChanged = !oldData ||
            newData.matchedFiles.length !== oldData.matchedFiles.length ||
            newData.unmatchedFiles.length !== oldData.unmatchedFiles.length ||
            newData.totalFiles !== oldData.totalFiles;

          if (hasChanged) {
            this.initializeWithExistingData();
          }
        }
      },
      deep: true,
      immediate: true,
    },
  },

  methods: {
    handleBibUpdate(data: any): void {
      this.bibData = {
        fileName: data.fileName || "",
        dataframeData: data.dataframeData || null,
        rawContent: data.rawContent || "",
      };
      this.emitBibUpdate();
    },

    handlePdfUpdate(data: any): void {
      this.pdfData = {
        matchedFiles: data.matchedFiles || [],
        unmatchedFiles: data.unmatchedFiles || [],
        totalFiles: data.totalFiles || 0,
      };

      // Update dataframe data with matched file paths
      this.updateDataframeWithFilePaths(data.matchedFiles || []);

      this.emitPdfUpdate();
    },

    // Event emitters
    emitBibUpdate(): void {
      this.$emit("bib-update", {
        isValid: this.bibData.dataframeData && this.bibData.dataframeData.data.length > 0,
        fileName: this.bibData.fileName,
        dataframeData: this.bibData.dataframeData,
        rawContent: this.bibData.rawContent,
      });
    },

    emitPdfUpdate(): void {
      this.$emit("pdf-update", {
        isValid: this.pdfData.matchedFiles.length > 0,
        matchedFiles: this.pdfData.matchedFiles,
        unmatchedFiles: this.pdfData.unmatchedFiles,
        totalFiles: this.pdfData.totalFiles,
      });
    },

    updateDataframeWithFilePaths(matchedFiles: any[]): void {
      if (!this.bibData.dataframeData || !matchedFiles.length) {
        return;
      }

      // Create a map of reference to file paths
      const referenceToFiles = new Map<string, string[]>();

      matchedFiles.forEach((matchedFile: any) => {
        const reference = matchedFile.bibEntry?.reference;
        const fileName = matchedFile.file?.name;

        if (reference && fileName) {
          if (!referenceToFiles.has(reference)) {
            referenceToFiles.set(reference, []);
          }
          referenceToFiles.get(reference)!.push(fileName);
        }
      });
      // Update the dataframe data with file paths
      const updatedData = this.bibData.dataframeData.data.map((row: any) => {
        const reference = row.reference || row.key;
        const filePaths = referenceToFiles.get(reference) || [];

        return {
          ...row,
          filePaths: filePaths
        };
      });

      // Update the dataframe data
      this.bibData.dataframeData = {
        ...this.bibData.dataframeData,
        data: updatedData
      };

      // Re-emit the bib update with the updated dataframe
      this.emitBibUpdate();
    },

    // Initialize component with existing data when navigating back
    initializeWithExistingData(): void {
      // Set flag to prevent recursive updates
      this.isInitializing = true;

      // Initialize bibliography data
      if (this.initialBibData && (this.initialBibData.fileName || (this.initialBibData.dataframeData && this.initialBibData.dataframeData.data.length > 0))) {
        this.bibData = {
          fileName: this.initialBibData.fileName || "",
          dataframeData: this.initialBibData.dataframeData || null,
          rawContent: this.initialBibData.rawContent || "",
        };
      }

      // Initialize PDF data
      if (this.initialPdfData && (this.initialPdfData.matchedFiles.length > 0 || this.initialPdfData.unmatchedFiles.length > 0 || this.initialPdfData.totalFiles > 0)) {
        this.pdfData = {
          matchedFiles: this.initialPdfData.matchedFiles || [],
          unmatchedFiles: this.initialPdfData.unmatchedFiles || [],
          totalFiles: this.initialPdfData.totalFiles || 0,
        };
      }

      // Clear the initialization flag and emit updates after all data is set
      this.$nextTick(() => {
        this.isInitializing = false;
        // Emit updates to parent to ensure consistency
        this.emitBibUpdate();
        this.emitPdfUpdate();
      });
    },

    // Public methods for parent components
    reset(): void {
      // Set flag to prevent recursive updates during reset
      this.isInitializing = true;

      // Reset bibliography data
      this.bibData = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };

      // Reset PDF data
      this.pdfData = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      };

      // Clear the initialization flag and emit updates after reset
      this.$nextTick(() => {
        this.isInitializing = false;
        this.emitBibUpdate();
        this.emitPdfUpdate();
      });
    },
  },
};
</script>
<style lang="scss" scoped>
.import-file-upload {
  padding: $base-space * 3;

  &__header {
    text-align: center;
    margin-bottom: $base-space * 3;
  }

  &__title {
    font-size: 1.5rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__description {
    color: var(--fg-secondary);
    margin-bottom: 0;
  }

  &__content {
    display: flex;
    gap: $base-space * 3;

    @media (max-width: 768px) {
      flex-direction: column;
    }
  }

  &__main {
    flex: 2;
    display: flex;
    flex-direction: column;
    gap: $base-space * 3;
  }

  &__sidebar {
    flex: 1;
    background: var(--bg-accent-grey-1);
    border: 1px solid var(--border-field);
    border-radius: $border-radius-m;
    padding: $base-space * 2;
    height: fit-content;
    position: sticky;
    top: $base-space * 2;
  }

  &__section {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
  }

  &__section-header {
    margin-bottom: $base-space * 2;
  }

  &__section-title {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__section-icon {
    font-size: 1.2rem;
    color: var(--fg-secondary);
  }

  &__section-description {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    margin-bottom: 0;
    line-height: 1.4;
  }

  &__dropzone {
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

  &__dropzone-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: $base-space;
  }

  &__dropzone-icon {
    font-size: 3rem;
    color: var(--fg-secondary);
  }

  &__dropzone-text {
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--fg-primary);
    margin: 0;
  }

  &__dropzone-subtext {
    font-size: 0.9rem;
    color: var(--fg-secondary);
    margin: 0;
  }

  &__dropzone-buttons {
    display: flex;
    gap: $base-space;
    margin-top: $base-space;
  }

  &__progress {
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);
  }

  &__progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $base-space;

    h4 {
      margin: 0;
      font-size: 1rem;
      color: var(--fg-primary);
    }

    span {
      font-size: 0.9rem;
      color: var(--fg-secondary);
    }
  }

  &__progress-bar {
    width: 100%;
    height: 8px;
    background: var(--bg-accent-grey-3);
    border-radius: $border-radius-s;
    overflow: hidden;
  }

  &__progress-fill {
    height: 100%;
    background: var(--bg-action);
    border-radius: $border-radius-s;
    transition: width 0.3s ease;
  }

  &__success {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border: 1px solid var(--color-success);
    border-radius: $border-radius;
  }

  &__success-icon {
    color: var(--color-success);
    font-size: 1.2rem;
  }

  &__success-content h4 {
    margin: 0 0 calc($base-space / 2) 0;
    color: var(--color-success);
    font-size: 1rem;
  }

  &__success-content p {
    margin: 0;
    color: var(--fg-primary);
  }

  &__error {
    display: flex;
    align-items: flex-start;
    gap: $base-space;
    padding: $base-space * 2;
    background: var(--bg-banner-error);
    border: 1px solid var(--color-danger);
    border-radius: $border-radius;
  }

  &__error-icon {
    color: var(--color-danger);
    font-size: 1.2rem;
    margin-top: 0.1rem;
  }

  &__error-content h4 {
    margin: 0 0 $base-space 0;
    color: var(--color-danger);
    font-size: 1rem;
  }

  &__error-content p {
    margin: 0;
    color: var(--fg-primary);
  }

  &__upload-success {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-solid-grey-2);
    border: 1px solid var(--color-success);
    border-radius: $border-radius;
    margin-top: $base-space;
  }

  &__upload-success-icon {
    color: var(--color-success);
    font-size: 1rem;
    flex-shrink: 0;
  }

  &__upload-success-text {
    color: var(--fg-primary);
    font-size: 0.9rem;
    font-weight: 500;
  }

  &__match-info {
    color: var(--color-success);
    font-weight: 600;
  }

  &__sidebar-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__sidebar-stats {
    display: flex;
    flex-direction: column;
    gap: $base-space * 2;
    margin-bottom: $base-space * 3;
  }

  &__sidebar-stat {
    display: flex;
    align-items: flex-start;
    gap: $base-space;
  }

  &__sidebar-stat-icon {
    font-size: 1.2rem;
    margin-top: 0.1rem;
    flex-shrink: 0;

    &--bib {
      color: var(--color-danger);
    }

    &--pdf {
      color: var(--fg-secondary);
    }

    &--match {
      color: var(--color-success);
    }
  }

  &__sidebar-stat-text {
    color: var(--fg-primary);
    font-size: 0.9rem;
    line-height: 1.4;
  }

  &__sidebar-action {
    margin-top: auto;
    padding-top: $base-space * 2;
    border-top: 1px solid var(--border-field);
  }

  &__preview-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
    text-align: center;
  }

  &__stats {
    display: flex;
    justify-content: center;
    gap: $base-space * 2;
    margin-bottom: $base-space * 3;
    flex-wrap: wrap;
  }

  &__stat {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space;
    background: var(--bg-accent-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);

    &--success {
      border-color: var(--color-success);
      background: var(--bg-solid-grey-2);
    }

    &--warning {
      border-color: var(--color-warning);
      background: var(--bg-banner-warning);
    }
  }

  &__stat-icon {
    font-size: 1.2rem;
    color: var(--fg-secondary);

    .import-file-upload__stat--success & {
      color: var(--color-success);
    }

    .import-file-upload__stat--warning & {
      color: var(--color-warning);
    }
  }

  &__stat-content {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 4);
  }

  &__stat-value {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--fg-primary);
  }

  &__stat-label {
    font-size: 0.9rem;
    color: var(--fg-secondary);
  }

  &__quick-preview {
    margin-top: $base-space * 2;
  }

  &__quick-preview-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: $base-space * 2;
    color: var(--fg-primary);
  }

  &__table-container {
    overflow-x: auto;
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
  }

  &__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;

    th {
      background: var(--bg-accent-grey-2);
      padding: $base-space;
      text-align: left;
      font-weight: 600;
      color: var(--fg-primary);
      border-bottom: 1px solid var(--border-field);
    }

    td {
      padding: $base-space;
      border-bottom: 1px solid var(--border-field);
      color: var(--fg-primary);
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover {
      background: var(--bg-accent-grey-3);
    }
  }

  &__table-cell {
    &--key {
      font-family: $quaternary-font-family;
      font-weight: 600;
      color: var(--bg-action);
    }

    &--title {
      font-weight: 500;
      max-width: 250px;
    }

    &--filename {
      display: flex;
      align-items: center;
      gap: calc($base-space / 2);
      font-weight: 500;
      max-width: 200px;
    }

    &--match {
      text-align: center;
    }
  }

  &__file-icon {
    color: var(--color-danger);
    font-size: 1rem;
    flex-shrink: 0;
  }

  &__match-badge {
    display: inline-block;
    padding: calc($base-space / 4) calc($base-space / 2);
    border-radius: $border-radius-s;
    font-size: 0.8rem;
    font-weight: 500;
    text-transform: uppercase;

    &--exact {
      background: var(--color-success);
      color: white;
    }

    &--partial {
      background: var(--bg-action);
      color: white;
    }

    &--file_field {
      background: var(--bg-action);
      color: white;
    }

    &--title {
      background: var(--color-warning);
      color: white;
    }
  }

  &__preview-note {
    margin-top: $base-space * 2;
    text-align: center;

    p {
      margin: 0;
      font-size: 0.9rem;
      color: var(--fg-secondary);
      font-style: italic;
    }
  }

  // CSV Column Selection Styles
  &__csv-selection {
    margin-top: $base-space * 2;
    padding: $base-space * 2;
    background: var(--bg-accent-grey-2);
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
  }

  &__csv-selection-header {
    margin-bottom: $base-space * 2;
  }

  &__csv-selection-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: $base-space;
    color: var(--fg-primary);
  }

  &__csv-selection-description {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    margin-bottom: 0;
    line-height: 1.4;
  }

  &__csv-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: $base-space * 2;
    margin-bottom: $base-space * 2;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }
  }

  &__csv-column-group {
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__csv-column-label {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--fg-primary);
    display: flex;
    flex-direction: column;
    gap: calc($base-space / 2);
  }

  &__csv-column-select {
    padding: calc($base-space / 2) $base-space;
    border: 1px solid var(--border-field);
    border-radius: $border-radius-s;
    background: var(--bg-solid-grey-1);
    color: var(--fg-primary);
    font-size: 0.9rem;

    &:focus {
      outline: none;
      border-color: var(--bg-action);
      box-shadow: 0 0 0 2px var(--bg-action-alpha);
    }
  }

  &__csv-column-help {
    font-size: 0.8rem;
    color: var(--fg-secondary);
    margin: 0;
    line-height: 1.3;
  }

  &__csv-preview {
    margin-bottom: $base-space * 2;

    h5 {
      font-size: 0.9rem;
      font-weight: 600;
      margin-bottom: $base-space;
      color: var(--fg-primary);
    }
  }

  &__csv-preview-table {
    overflow-x: auto;
    border: 1px solid var(--border-field);
    border-radius: $border-radius-s;
    background: var(--bg-solid-grey-1);
  }

  &__csv-preview-header--selected {
    background: var(--bg-action-alpha) !important;
    color: var(--bg-action) !important;
    font-weight: 600;
    position: relative;
  }

  &__csv-preview-cell--selected {
    background: var(--bg-action-alpha) !important;
    font-weight: 500;
  }

  &__csv-preview-badge {
    display: inline-block;
    padding: 2px 6px;
    background: var(--bg-action);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    border-radius: $border-radius-s;
    margin-left: calc($base-space / 2);
    text-transform: uppercase;
  }

  &__csv-actions {
    display: flex;
    gap: $base-space;
    justify-content: flex-end;

    @media (max-width: 768px) {
      flex-direction: column;
    }
  }
}
</style>
