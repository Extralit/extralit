<template>
  <div class="import-analysis-table">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <BaseSpinner />
      <p>Analyzing import status...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="hasError" class="error-state">
      <BaseIcon name="danger" class="error-icon" />
      <div class="error-content">
        <h4>Analysis Failed</h4>
        <p>{{ errorMessage }}</p>
        <BaseButton variant="outline" @click="$emit('retry')">
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
            <span class="stat-value">{{ analysisData.summary.total_documents }}</span>
          </div>
          <div class="stat-item stat-add">
            <span class="stat-label">Add:</span>
            <span class="stat-value">{{ analysisData.summary.add_count }}</span>
          </div>
          <div class="stat-item stat-update">
            <span class="stat-label">Update:</span>
            <span class="stat-value">{{ analysisData.summary.update_count }}</span>
          </div>
          <div class="stat-item stat-skip">
            <span class="stat-label">Skip:</span>
            <span class="stat-value">{{ analysisData.summary.skip_count }}</span>
          </div>
          <div class="stat-item stat-failed">
            <span class="stat-label">Failed:</span>
            <span class="stat-value">{{ analysisData.summary.failed_count }}</span>
          </div>
        </div>
      </div>

      <!-- Table -->
      <div class="table-container">
        <BaseSimpleTable
          :data="tableData"
          :columns="tableColumns"
          :options="tableOptions"
          @cell-edited="handleCellEdit"
        />
      </div>

    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/chevron-down";
import type {
  ImportAnalysisData,
  ImportConfirmationData,
  AnalysisTableRow,
  TableColumn,
  ImportStatus,
  DataframeData,
  BibTexEntry
} from './types';

export default {
  name: "ImportAnalysisTable",

  props: {
    analysisData: {
      type: Object as () => ImportAnalysisData,
      default: (): ImportAnalysisData => ({
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0,
        },
      }),
    },
    // Add dataframe data prop for direct table display
    dataframeData: {
      type: Object as () => DataframeData | null,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },

  emits: ["update", "retry"],

  data() {
    return {
      hasError: false,
      errorMessage: "",
      documentActions: {} as Record<string, ImportStatus>, // Track user-modified actions for each document
      originalStatuses: {} as Record<string, ImportStatus>, // Track original statuses from analysis
    };
  },

  computed: {
    tableData(): AnalysisTableRow[] {
      // If we have dataframe data, use it directly for table display
      if (this.dataframeData && this.dataframeData.data.length > 0) {
        return this.dataframeData.data.map((row: Record<string, any>) => {
          const reference = row.reference || row.key || `row_${Math.random()}`;
          const currentAction = this.documentActions[reference] || 'add';

          return {
            reference,
            title: row.title || "N/A",
            authors: this.formatAuthors(row.authors || row.author),
            year: String(row.year || "N/A"),
            files: "No files", // Files will be matched separately
            status: currentAction,
            originalStatus: 'add', // Default for new entries
            validationErrors: [],
            canToggle: true,
          };
        });
      }

      // Fallback to analysis data structure
      const data: AnalysisTableRow[] = [];

      Object.entries(this.analysisData.documents || {}).forEach(([reference, docInfo]: [string, any]) => {
        // Get current action (user-modified or original)
        const currentAction = this.documentActions[reference] || docInfo.status;

        data.push({
          reference,
          title: docInfo.document_create?.title || "N/A",
          authors: this.formatAuthors(docInfo.document_create?.authors),
          year: docInfo.document_create?.year || "N/A",
          files: this.formatFiles(docInfo.associated_files),
          status: currentAction,
          originalStatus: docInfo.status,
          validationErrors: docInfo.validation_errors || [],
          canToggle: this.canToggleStatus(docInfo.status),
        });
      });

      return data;
    },

    tableColumns(): TableColumn[] {
      return [
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
        {
          field: "files",
          title: "Files",
          width: 150,
          formatter: this.filesFormatter,
          // visible: !this.dataframeData, // Hide files column for dataframe-only display
        },
        {
          field: "status",
          title: "Import Status",
          width: 150,
          frozen: true,
          formatter: this.statusFormatter,
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
          // visible: !this.dataframeData, // Hide status column for dataframe-only display
        },
      ];
    },

    tableOptions() {
      return {
        height: "400px",
        layout: "fitDataTable",
        pagination: true,
        paginationSize: 20,
        paginationSizeSelector: [10, 20, 50],
        sortMode: "local",
        filterMode: "local",
        responsiveLayout: "hide",
        placeholder: "No documents to analyze",
      };
    },

    confirmedCount() {
      return Object.values(this.documentActions).filter(action =>
        action === "add" || action === "update"
      ).length +
      Object.entries(this.analysisData.documents || {}).filter(([ref, docInfo]: [string, any]) =>
        !this.documentActions[ref] && (docInfo.status === "add" || docInfo.status === "update")
      ).length;
    },

    canConfirmImport() {
      return this.confirmedCount > 0;
    },
  },

  watch: {
    analysisData: {
      handler(newData) {
        // Reset document actions when new analysis data arrives
        this.documentActions = {};
        this.originalStatuses = {};

        // Store original statuses
        Object.entries(newData.documents || {}).forEach(([reference, docInfo]: [string, any]) => {
          this.originalStatuses[reference] = docInfo.status;
        });
      },
      deep: true,
      immediate: true,
    },
  },

  methods: {
    // Formatters for table cells
    referenceFormatter(cell) {
      const value = cell.getValue();
      return `<span class="reference-cell" title="${value}">${value}</span>`;
    },

    titleFormatter(cell) {
      const value = cell.getValue();
      const truncated = value.length > 50 ? value.substring(0, 50) + "..." : value;
      return `<span class="title-cell" title="${value}">${truncated}</span>`;
    },

    authorsFormatter(cell) {
      const value = cell.getValue();
      const truncated = value.length > 30 ? value.substring(0, 30) + "..." : value;
      return `<span class="authors-cell" title="${value}">${truncated}</span>`;
    },

    filesFormatter(cell) {
      const files = cell.getValue();
      const fileCount = files.split(", ").length;
      return `<span class="files-cell" title="${files}">${fileCount} file${fileCount !== 1 ? 's' : ''}</span>`;
    },

    statusFormatter(cell) {
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
    formatAuthors(authors) {
      if (!authors || authors.length === 0) return "N/A";
      if (typeof authors === "string") return authors;
      if (Array.isArray(authors)) {
        return authors.join(", ");
      }
      return "N/A";
    },

    formatFiles(files) {
      if (!files || files.length === 0) return "No files";
      return files.join(", ");
    },

    getStatusText(status) {
      const statusMap = {
        add: "Add",
        update: "Update",
        skip: "Skip",
        ignore: "Ignore",
        failed: "Failed"
      };
      return statusMap[status] || status;
    },

    canToggleStatus(originalStatus) {
      // Can toggle from Add or Update to Skip
      return originalStatus === "add" || originalStatus === "update" || originalStatus === "ignore";
    },

    getNextStatus(currentStatus, originalStatus) {
      // Toggle between Add/Update and Skip
      if ((originalStatus === "add" || originalStatus === "update") && currentStatus !== "ignore") {
        return "ignore";
      } else if (currentStatus === "ignore") {
        return originalStatus; // Revert to original status
      }
      return currentStatus; // No change if can't toggle
    },

    // Event handlers
    handleStatusClick(e, cell) {
      const row = cell.getRow().getData();
      const currentStatus = row.status;
      const originalStatus = row.originalStatus;
      const reference = row.reference;

      if (!row.canToggle) return;

      const nextStatus = this.getNextStatus(currentStatus, originalStatus);
      if (nextStatus !== currentStatus) {
        // Update the document action
        this.$set(this.documentActions, reference, nextStatus);

        // Update the cell value
        cell.getRow().update({ status: nextStatus });

        // Emit update event
        this.emitUpdate();
      }
    },

    handleCellEdit(cell) {
      // Handle any cell edits if needed
      this.emitUpdate();
    },

    emitUpdate() {
      // Create confirmed documents object
      const confirmedDocuments = {};
      console.log(this.analysisData)

      Object.entries(this.analysisData.documents || {}).forEach(([reference, docInfo]: [string, any]) => {
        const finalAction = this.documentActions[reference] || docInfo.status;

        // Only include documents that will be processed (add or update)
        if (finalAction === "add" || finalAction === "update") {
          confirmedDocuments[reference] = {
            action: finalAction,
            document_create: docInfo.document_create,
            associated_files: docInfo.associated_files,
          };
        }
      });

      this.$emit("update", {
        confirmedDocuments,
        totalConfirmed: Object.keys(confirmedDocuments).length,
        documentActions: { ...this.documentActions },
      });
    },

    reset() {
      this.hasError = false;
      this.errorMessage = "";
      this.documentActions = {};
      this.originalStatuses = {};
    },

    showError(message) {
      this.hasError = true;
      this.errorMessage = message;
    },
  },
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

// Table container
.table-container {
  flex: 1;
  min-height: 300px;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  overflow: hidden;
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
