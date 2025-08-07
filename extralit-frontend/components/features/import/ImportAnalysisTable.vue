<template>
  <div class="import-analysis-table">
    <!-- Loading state -->
    <div v-if="loading || isAnalyzing" class="loading-state">
      <BaseSpinner />
      <p>{{ isAnalyzing ? 'Analyzing import status...' : 'Loading...' }}</p>
    </div>

    <!-- Error state -->
    <div v-else-if="hasError" class="error-state">
      <BaseIcon icon-name="danger" class="error-icon" />
      <div class="error-content">
        <h4>Analysis Failed</h4>
        <p>{{ errorMessage }}</p>
        <BaseButton variant="outline" @click="retryAnalysis">
          Retry Analysis
        </BaseButton>
      </div>
    </div>

    <!-- Main content -->
    <div v-else class="analysis-content">
      <!-- Summary header -->
      <div class="analysis-summary">
        <h3>Import Analysis Results</h3>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-label">Total:</span>
            <span class="stat-value">{{ summaryData.total_documents }}</span>
          </div>
          <div class="stat-item stat-add">
            <span class="stat-label">Add:</span>
            <span class="stat-value">{{ summaryData.add_count }}</span>
          </div>
          <div class="stat-item stat-update">
            <span class="stat-label">Update:</span>
            <span class="stat-value">{{ summaryData.update_count }}</span>
          </div>
          <div class="stat-item stat-skip">
            <span class="stat-label">Skip:</span>
            <span class="stat-value">{{ summaryData.skip_count }}</span>
          </div>
          <div class="stat-item stat-failed">
            <span class="stat-label">Failed:</span>
            <span class="stat-value">{{ summaryData.failed_count }}</span>
          </div>
        </div>
      </div>

      <!-- Import options -->
      <div class="import-options">
        <h4>Import Options</h4>
        <div class="option-group">
          <BaseRadioButton v-model="importMode" value="all" name="import-mode" @change="handleImportModeChange">
            Import all references (including those without PDFs)
          </BaseRadioButton>
          <BaseRadioButton v-model="importMode" value="with-pdfs" name="import-mode" @change="handleImportModeChange">
            Import only references with at least one PDF file
          </BaseRadioButton>
        </div>
        <div class="option-stats">
          <span class="stat-info">
            References without PDFs: {{ referencesWithoutPdfsCount }}
          </span>
          <span class="stat-info">
            References with PDFs: {{ referencesWithPdfsCount }}
          </span>
        </div>
      </div>

      <!-- Table -->
      <div class="table-container">
        <BaseSimpleTable :data="tableData" :columns="tableColumns" :options="tableOptions" />
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/chevron-down";
import type {
  ImportAnalysisResponse,
  ImportStatus,
  DataframeData,
  DocumentImportAnalysis,
} from '~/v1/domain/entities/import/ImportAnalysis';
import type {
  AnalysisTableRow,
  TableColumn,
  CellComponent,
  ImportDataFrameMode,
} from './types';
import { useImportAnalysisViewModel } from './useImportAnalysisViewModel';
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";

export default {
  name: "ImportAnalysisTable",

  props: {
    dataframeData: {
      type: Object as () => DataframeData | null,
      default: null,
    },
    pdfData: {
      type: Object,
      default: () => ({ matchedFiles: [] }),
    },
    workspace: {
      type: Workspace,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },

  emits: ["update", "analysis-complete"],

  data() {
    return {
      localDocumentActions: {} as Record<string, ImportStatus>,
      importMode: 'all' as ImportDataFrameMode, // Default to import all references
    };
  },

  computed: {
    summaryData() {
      if (this.analysisResult) {
        return this.analysisResult.summary;
      }

      // Default summary when no analysis result
      return {
        total_documents: this.dataframeData?.data?.length || 0,
        add_count: this.dataframeData?.data?.length || 0,
        update_count: 0,
        skip_count: 0,
        failed_count: 0,
      };
    },

    allTableData(): AnalysisTableRow[] {
      if (!this.dataframeData || !this.dataframeData.data.length) {
        return [];
      }

      const documentActions = { ...this.documentActions, ...this.localDocumentActions };

      return this.dataframeData.data.map((row: Record<string, any>) => {
        const reference = row.reference || row.key || `row_${Math.random()}`;

        // Get analysis info if available
        const analysisInfo = this.analysisResult?.documents?.[reference];
        const currentStatus = documentActions[reference] || analysisInfo?.status || 'add';
        const originalStatus = analysisInfo?.status || 'add';
        const validationErrors = analysisInfo?.validation_errors || [];

        // Use pre-processed file paths from ImportFileUpload.vue
        const filePaths = row.filePaths || [];

        // Create base row data
        const rowData: AnalysisTableRow = {
          reference,
          title: row.title || "N/A",
          authors: this.formatAuthors(row.authors || row.author),
          year: String(row.year || "N/A"),
          files: filePaths.length > 0 ? this.formatFiles(filePaths) : "No files",
          filePaths,
          status: currentStatus,
          originalStatus,
          validationErrors,
          canToggle: this.canToggleStatus(originalStatus) && !this.isAnalyzing,
        };

        // Add all other dataframe fields dynamically
        Object.keys(row).forEach(key => {
          if (!['reference', 'title', 'authors', 'author', 'year', 'filePaths'].includes(key)) {
            rowData[key] = row[key];
          }
        });

        return rowData;
      });
    },

    tableData(): AnalysisTableRow[] {
      const allData = this.allTableData;

      // Filter based on import mode
      if (this.importMode === 'with-pdfs') {
        return allData.filter(row => row.filePaths && row.filePaths.length > 0);
      }

      return allData;
    },

    referencesWithoutPdfsCount(): number {
      return this.allTableData.filter(row => !row.filePaths || row.filePaths.length === 0).length;
    },

    referencesWithPdfsCount(): number {
      return this.allTableData.filter(row => row.filePaths && row.filePaths.length > 0).length;
    },

    filteredDataframeData(): DataframeData | null {
      if (!this.dataframeData) {
        return null;
      }

      // If mode is 'all', return original dataframe data
      if (this.importMode === 'all') {
        return this.dataframeData;
      }

      // If mode is 'with-pdfs', filter out references without PDFs
      const filteredData = this.dataframeData.data.filter((row: Record<string, any>) => {
        const filePaths = row.filePaths || [];
        return filePaths.length > 0;
      });

      return {
        ...this.dataframeData,
        data: filteredData,
      };
    },

    tableColumns(): TableColumn[] {
      const columns: TableColumn[] = [
        {
          field: "reference",
          title: "Reference",
          width: 150,
          frozen: true,
          formatter: this.referenceFormatter,
        },
        {
          field: "title",
          title: "Title",
          width: 300,
          formatter: this.titleFormatter,
        },
        {
          field: "authors",
          title: "Authors",
          width: 200,
          formatter: this.authorsFormatter,
        },
        {
          field: "year",
          title: "Year",
          width: 80,
        },
      ];

      // Add dynamic columns from dataframe schema
      if (this.dataframeData?.schema?.fields) {
        const excludedFields = ['reference', 'title', 'authors', 'author', 'year', 'filePaths', 'type'];

        this.dataframeData.schema.fields.forEach(field => {
          if (!excludedFields.includes(field.name)) {
            columns.push({
              field: field.name,
              title: this.formatColumnTitle(field.name),
              width: 150,
            });
          }
        });
      }

      // Add files and status columns at the end
      columns.push(
        {
          field: "files",
          title: "Files",
          width: 150,
          formatter: this.filesFormatter,
          frozen: true,
        },
        {
          field: "status",
          title: "Import Status",
          width: 150,
          formatter: this.statusFormatter,
          frozen: true,
          cellClick: this.handleStatusClick,
          headerFilter: "select",
          headerFilterParams: {
            values: {
              "": "All",
              "add": "Add",
              "update": "Update",
              "skip": "Skip",
              "ignore": "Ignore",
              "failed": "Failed"
            }
          },
        }
      );
      return columns;
    },

    tableOptions() {
      return {
        layout: "fitData",
        pagination: true,
        paginationSize: 20,
        paginationSizeSelector: [10, 20, 50],
        sortMode: "local",
        filterMode: "local",
        placeholder: "No documents to analyze",
      };
    },

    confirmedCount() {
      const documentActions = { ...this.documentActions, ...this.localDocumentActions };
      let count = 0;

      if (this.analysisResult) {
        // Count from analysis result
        Object.entries(this.analysisResult.documents).forEach(([ref, docInfo]: [string, DocumentImportAnalysis]) => {
          const finalAction = documentActions[ref] || docInfo.status;
          const hasFiles = docInfo.associated_files && docInfo.associated_files.length > 0;

          // Respect import mode: skip references without PDFs if mode is 'with-pdfs'
          if (this.importMode === 'with-pdfs' && !hasFiles) {
            return;
          }

          if (finalAction === "add" || finalAction === "update") {
            count++;
          }
        });
      } else if (this.dataframeData) {
        // Count from dataframe data (default to add)
        this.dataframeData.data.forEach((row: Record<string, any>) => {
          const reference = row.reference || row.key;
          const finalAction = documentActions[reference] || 'add';
          const filePaths = row.filePaths || [];
          const hasFiles = filePaths.length > 0;

          // Respect import mode: skip references without PDFs if mode is 'with-pdfs'
          if (this.importMode === 'with-pdfs' && !hasFiles) {
            return;
          }

          if (finalAction === "add" || finalAction === "update") {
            count++;
          }
        });
      }

      return count;
    },

    canConfirmImport() {
      return this.confirmedCount > 0;
    },
  },

  watch: {
    analysisResult: {
      handler(newData: ImportAnalysisResponse) {
        if (newData) {
          // Reset local document actions when new analysis data arrives
          this.localDocumentActions = {};
          // Emit the analysis complete event
          this.$emit('analysis-complete', newData);
          // Emit initial update
          this.emitUpdate();
        }
      },
      deep: true,
    },
  },

  methods: {
    // Formatters for table cells
    referenceFormatter(cell: CellComponent) {
      const value = cell.getValue();
      return `<span class="reference-cell">${value}</span>`;
    },

    titleFormatter(cell: CellComponent) {
      const value = cell.getValue();
      return `<span class="title-cell">${value}</span>`;
    },

    authorsFormatter(cell: CellComponent) {
      const value = cell.getValue();
      return `<span class="authors-cell">${value}</span>`;
    },

    filesFormatter(cell: CellComponent) {
      const files = cell.getValue();
      if (files === "No files") {
        return `<span class="files-cell no-files">${files}</span>`;
      }
      const fileCount = files.split(", ").filter((f: string) => f.trim().length > 0).length;
      return `<span class="files-cell" title="${files}">${fileCount} file${fileCount !== 1 ? 's' : ''}</span>`;
    },

    statusFormatter(cell: CellComponent) {
      const status = cell.getValue();
      const row = cell.getRow().getData();
      const canToggle = row.canToggle;

      const statusClass = `status-${status}`;
      const statusText = this.getStatusText(status);
      const toggleIcon = canToggle ? '<span class="status-toggle">▼</span>' : '';

      return `
        <div class="status-cell ${statusClass} ${canToggle ? 'clickable' : ''}">
          <span class="status-indicator"></span>
          <span class="status-text">${statusText}</span>
          ${toggleIcon}
        </div>
      `;
    },

    // Helper methods
    formatAuthors(authors: any) {
      if (!authors || authors.length === 0) return "N/A";
      if (typeof authors === "string") return authors;
      if (Array.isArray(authors)) {
        return authors.join(", ");
      }
      return "N/A";
    },

    formatFiles(files: any) {
      if (!files || files.length === 0) return "No files";
      return files.join(", ");
    },



    getStatusText(status: string) {
      const statusMap = {
        add: "Add",
        update: "Update",
        skip: "Skip",
        ignore: "Ignore",
        failed: "Failed"
      };
      return statusMap[status] || status;
    },

    canToggleStatus(originalStatus: ImportStatus) {
      return originalStatus === "add" || originalStatus === "update" || originalStatus === "ignore";
    },

    getNextStatus(currentStatus: ImportStatus, originalStatus: ImportStatus) {
      if ((originalStatus === "add" || originalStatus === "update") && currentStatus !== "ignore") {
        return "ignore";
      } else if (currentStatus === "ignore") {
        return originalStatus;
      }
      return currentStatus;
    },

    // Event handlers
    handleStatusClick(_e: any, cell: CellComponent) {
      const row = cell.getRow().getData();
      const currentStatus = row.status;
      const originalStatus = row.originalStatus;
      const reference = row.reference;

      if (!row.canToggle || this.isAnalyzing) return;

      const nextStatus = this.getNextStatus(currentStatus, originalStatus);
      if (nextStatus !== currentStatus) {
        // Update the local document action
        this.$set(this.localDocumentActions, reference, nextStatus);

        // Update the cell value
        cell.getRow().update({ status: nextStatus });

        // Emit update event
        this.emitUpdate();
      }
    },

    handleImportModeChange() {
      // When import mode changes, automatically set references without PDFs to ignore if mode is 'with-pdfs'
      if (this.importMode === 'with-pdfs') {
        this.allTableData.forEach(row => {
          if (!row.filePaths || row.filePaths.length === 0) {
            // Set references without PDFs to ignore
            this.$set(this.localDocumentActions, row.reference, 'ignore');
          }
        });
      } else if (this.importMode === 'all') {
        // When switching back to 'all', restore original status for references without PDFs
        this.allTableData.forEach(row => {
          if (!row.filePaths || row.filePaths.length === 0) {
            // Remove from local actions to restore original status
            if (this.localDocumentActions[row.reference] === 'ignore') {
              this.$delete(this.localDocumentActions, row.reference);
            }
          }
        });
      }

      // Emit update to reflect the changes
      this.emitUpdate();
    },


    formatColumnTitle(fieldName: string) {
      // Convert field names to readable titles
      return fieldName
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase())
        .trim();
    },




    emitUpdate() {
      const confirmedDocuments: Record<string, any> = {};
      const documentActions = { ...this.documentActions, ...this.localDocumentActions };

      // Handle analysis data case (preferred)
      if (this.analysisResult && this.analysisResult.documents && Object.keys(this.analysisResult.documents).length > 0) {
        Object.entries(this.analysisResult.documents).forEach(([reference, docInfo]: [string, DocumentImportAnalysis]) => {
          const finalAction = documentActions[reference] || docInfo.status;
          const hasFiles = docInfo.associated_files && docInfo.associated_files.length > 0;

          // Respect import mode: skip references without PDFs if mode is 'with-pdfs'
          if (this.importMode === 'with-pdfs' && !hasFiles) {
            return;
          }

          // Only include documents that will be processed (add or update)
          if (finalAction === "add" || finalAction === "update") {
            // Ensure metadata is included in document_create
            const documentCreate = {
              ...docInfo.document_create,
              metadata: {
                source: "bib_import",
                collections: [this.workspace?.name || "default"],
                ...docInfo.document_create.metadata,
              },
            };

            confirmedDocuments[reference] = {
              document_create: documentCreate,
              associated_files: docInfo.associated_files || [],
            };
          }
        });
      } else if (this.dataframeData && this.dataframeData.data.length > 0) {
        this.dataframeData.data.forEach((row: Record<string, any>) => {
          const reference = row.reference || row.key || `row_${Math.random()}`;
          const finalAction = documentActions[reference] || 'add';
          const filePaths = row.filePaths || [];
          const hasFiles = filePaths.length > 0;

          // Respect import mode: skip references without PDFs if mode is 'with-pdfs'
          if (this.importMode === 'with-pdfs' && !hasFiles) {
            return;
          }

          // Only include documents that will be processed (add or update)
          if (finalAction === "add" || finalAction === "update") {
            confirmedDocuments[reference] = {
              document_create: {
                reference,
                title: row.title,
                authors: Array.isArray(row.authors) ? row.authors : (row.authors ? [row.authors] : undefined),
                year: row.year ? String(row.year) : undefined,
                journal: row.journal,
                volume: row.volume,
                pages: row.pages,
                doi: row.doi,
                url: row.url,
                abstract: row.abstract,
                keywords: Array.isArray(row.keywords) ? row.keywords : (row.keywords ? [row.keywords] : undefined),
                pmid: row.pmid,
                workspace_id: this.workspace?.id,
                metadata: {
                  source: "bib_import",
                  collections: [this.workspace?.name || "default"],
                },
              },
              associated_files: filePaths.map((filename: string) => ({
                filename,
                size: this.getFileSize(filename) || 0
              })),
            };
          }
        });
      }

      this.$emit("update", {
        confirmedDocuments,
        totalConfirmed: Object.keys(confirmedDocuments).length,
        documentActions: documentActions,
        importMode: this.importMode,
        filteredDataframeData: this.filteredDataframeData,
      });
    },

    getFileSize(filename: string): number {
      // Try to find the file size from matched files
      if (this.pdfData?.matchedFiles) {
        const matchedFile = this.pdfData.matchedFiles.find((mf: any) => mf.file.name === filename);
        if (matchedFile) {
          return matchedFile.file.size || 0;
        }
      }
      return 0;
    },

    resetLocalState() {
      this.localDocumentActions = {};
      this.importMode = 'all';
    },


    // Helper method to prepare data for ImportHistoryCreate payload
    getImportHistoryData() {
      if (this.dataframeData) {
        // Return dataframe data in the format expected by ImportHistoryCreate.data
        return this.dataframeData;
      }

      // Convert analysis data to dataframe format if needed
      if (this.analysisResult && this.analysisResult.documents) {
        const dataRows: any[] = [];
        Object.entries(this.analysisResult.documents).forEach(([reference, docInfo]: [string, any]) => {
          dataRows.push({
            reference,
            title: docInfo.document_create?.title || "",
            authors: Array.isArray(docInfo.document_create?.authors)
              ? docInfo.document_create.authors.join(", ")
              : docInfo.document_create?.authors || "",
            year: docInfo.document_create?.year || "",
            doi: docInfo.document_create?.doi || "",
            pmid: docInfo.document_create?.pmid || "",
            journal: docInfo.document_create?.journal || "",
            abstract: docInfo.document_create?.abstract || "",
            file: docInfo.associated_files.join(";"), // Store file paths as semicolon-separated
          });
        });

        return {
          schema: {
            fields: [
              { name: "reference", type: "string" },
              { name: "title", type: "string" },
              { name: "authors", type: "string" },
              { name: "year", type: "string" },
              { name: "doi", type: "string" },
              { name: "pmid", type: "string" },
              { name: "journal", type: "string" },
              { name: "abstract", type: "string" },
              { name: "file", type: "string" },
            ],
            primaryKey: ["reference"]
          },
          data: dataRows
        };
      }

      return null;
    },
  },

  setup(props) {
    return useImportAnalysisViewModel(props);
  }
};
</script>

<style lang="scss" scoped>
.import-analysis-table {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 500px;
}

// Loading state
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: $base-space * 2;

  p {
    color: var(--fg-secondary);
    font-size: $base-font-size;
  }
}

// Error state
.error-state {
  display: flex;
  align-items: flex-start;
  gap: $base-space * 2;
  padding: $base-space * 3;
  background: var(--bg-banner-error);
  border: 1px solid var(--color-danger);
  border-radius: $border-radius;
  margin: $base-space * 2 0;

  .error-icon {
    color: var(--color-danger);
    font-size: 1.5rem;
    flex-shrink: 0;
  }

  .error-content {
    flex: 1;

    h4 {
      margin: 0 0 $base-space 0;
      color: var(--color-danger);
      font-weight: 600;
      font-size: 1.1rem;
    }

    p {
      margin: 0 0 $base-space * 2 0;
      color: var(--fg-primary);
      font-size: 0.9rem;
    }
  }
}

// Main content
.analysis-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: $base-space * 2;
}

// Summary header
.analysis-summary {
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  h3 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1.2rem;
    font-weight: 600;
  }

  .summary-stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;

    .stat-item {
      display: flex;
      align-items: center;
      gap: $base-space;

      .stat-label {
        color: var(--fg-secondary);
        font-size: 0.9rem;
      }

      .stat-value {
        font-weight: 600;
        font-size: 1rem;
        color: var(--fg-primary);
      }

      &.stat-add .stat-value {
        color: var(--color-success);
      }

      &.stat-update .stat-value {
        color: var(--bg-action);
      }

      &.stat-skip .stat-value {
        color: var(--fg-secondary);
      }

      &.stat-failed .stat-value {
        color: var(--color-danger);
      }
    }
  }
}

// Import options
.import-options {
  padding: $base-space * 2;
  background: var(--bg-solid-grey-1);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  h4 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1rem;
    font-weight: 600;
  }

  .option-group {
    display: flex;
    flex-direction: column;
    gap: $base-space;
    margin-bottom: $base-space * 2;
  }

  .option-stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;
    padding-top: $base-space;
    border-top: 1px solid var(--border-field);

    .stat-info {
      color: var(--fg-secondary);
      font-size: 0.9rem;

      &:first-child {
        color: var(--fg-tertiary);
      }

      &:last-child {
        color: var(--color-success);
      }
    }
  }
}

// Table container
.table-container {
  min-height: 300px;
  border-radius: $border-radius;
  overflow: auto;
}

// Table cell styles (applied globally to override Tabulator)
:deep(.tabulator) {
  .reference-cell {
    font-family: $quaternary-font-family;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--fg-cuaternary);
  }

  .title-cell {
    font-weight: 500;
    color: var(--fg-primary);
  }

  .authors-cell {
    color: var(--fg-secondary);
    font-size: 0.9rem;
  }

  .files-cell {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    font-style: italic;

    &.no-files {
      color: var(--fg-tertiary);
      opacity: 0.7;
    }
  }

  .status-cell {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: 4px 8px;
    border-radius: $border-radius-s;
    font-weight: 500;
    font-size: 0.9rem;
    cursor: default;

    &.clickable {
      cursor: pointer;

      &:hover {
        opacity: 0.8;
      }
    }

    .status-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .status-toggle {
      margin-left: auto;
      font-size: 0.7rem;
      opacity: 0.6;
    }

    // Status-specific styling
    &.status-add {
      background: var(--color-success);
      color: white;

      .status-indicator {
        background: rgba(255, 255, 255, 0.8);
      }
    }

    &.status-update {
      background: var(--bg-action);
      color: white;

      .status-indicator {
        background: rgba(255, 255, 255, 0.8);
      }
    }

    &.status-skip {
      background: var(--bg-solid-grey-3);
      color: var(--fg-secondary);

      .status-indicator {
        background: var(--fg-tertiary);
      }
    }

    &.status-ignore {
      background: var(--bg-solid-grey-3);
      color: var(--fg-secondary);

      .status-indicator {
        background: var(--fg-tertiary);
      }
    }

    &.status-failed {
      background: var(--color-danger);
      color: white;

      .status-indicator {
        background: rgba(255, 255, 255, 0.8);
      }
    }
  }

  // Frozen column styling
  .tabulator-col.tabulator-frozen {
    background: var(--bg-accent-grey-2);
    border-right: 2px solid var(--border-field);
  }

  .tabulator-row .tabulator-cell.tabulator-frozen {
    background: var(--bg-accent-grey-2);
    border-right: 2px solid var(--border-field);
  }

  .tabulator-row:hover .tabulator-cell.tabulator-frozen {
    background: var(--bg-solid-grey-2);
  }
}
</style>
