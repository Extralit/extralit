<template>
  <div class="import-summary">
    <!-- Summary Header -->
    <div class="summary-header">
      <BaseIcon icon-name="check" class="summary-icon" />
      <h3>Import Complete</h3>
      <p class="summary-subtitle">
        Your document import has been processed successfully
      </p>
    </div>

    <!-- Import Statistics -->
    <div class="import-statistics">
      <div class="stats-grid">
        <div class="stat-card stat-total">
          <div class="stat-value">{{ normalizedSummary.total || 0 }}</div>
          <div class="stat-label">Total Processed</div>
        </div>

        <div class="stat-card stat-added">
          <div class="stat-value">{{ normalizedSummary.added || 0 }}</div>
          <div class="stat-label">Successfully Added</div>
        </div>

        <div class="stat-card stat-updated">
          <div class="stat-value">{{ normalizedSummary.updated || 0 }}</div>
          <div class="stat-label">Updated</div>
        </div>

        <div class="stat-card stat-skipped">
          <div class="stat-value">{{ normalizedSummary.skipped || 0 }}</div>
          <div class="stat-label">Skipped</div>
        </div>

        <div class="stat-card stat-failed">
          <div class="stat-value">{{ normalizedSummary.failed || 0 }}</div>
          <div class="stat-label">Failed</div>
        </div>
      </div>
    </div>

    <!-- Detailed Results Breakdown -->
    <div class="results-breakdown">
      <h4>Import Results</h4>

      <!-- Success Summary -->
      <div v-if="hasSuccessfulImports" class="result-section success-section">
        <div class="section-header">
          <BaseIcon icon-name="check" class="section-icon success-icon" />
          <span class="section-title">Successfully Imported</span>
          <span class="section-count">{{ successfulCount }}</span>
        </div>
        <p class="section-description">
          Documents have been added to your workspace and are ready for extraction workflows.
        </p>
      </div>

      <!-- Skipped Summary -->
      <div v-if="(normalizedSummary.skipped || 0) > 0" class="result-section skipped-section">
        <div class="section-header">
          <BaseIcon icon-name="info" class="section-icon skipped-icon" />
          <span class="section-title">Skipped Documents</span>
          <span class="section-count">{{ normalizedSummary.skipped || 0 }}</span>
        </div>
        <p class="section-description">
          Documents were skipped because they already exist in your workspace with no changes needed.
        </p>
      </div>

      <!-- Failed Summary -->
      <div v-if="(normalizedSummary.failed || 0) > 0" class="result-section failed-section">
        <div class="section-header">
          <BaseIcon icon-name="danger" class="section-icon failed-icon" />
          <span class="section-title">Failed Imports</span>
          <span class="section-count">{{ normalizedSummary.failed || 0 }}</span>
        </div>
        <p class="section-description">
          Some documents could not be imported due to errors. Review the details below.
        </p>
      </div>
    </div>

    <!-- Failed Imports Table -->
    <div v-if="hasFailedImports" class="failed-imports">
      <h4>Failed Import Details</h4>
      <div class="failed-table-container">
        <BaseSimpleTable
          :data="failedImportsTableData"
          :columns="failedImportsColumns"
          :options="failedTableOptions"
          class="failed-imports-table"
        />
      </div>

      <!-- Retry Options -->
      <div class="retry-section">
        <p class="retry-description">
          You can retry failed imports by fixing the issues and running the import process again.
        </p>
        <BaseButton
          variant="outline"
          @click="retryFailedImports"
          :disabled="isRetrying"
        >
          {{ isRetrying ? 'Retrying...' : 'Retry Failed Imports' }}
        </BaseButton>
      </div>
    </div>

    <!-- Import Metadata -->
    <div class="import-metadata">
      <h4>Import Information</h4>
      <div class="metadata-grid">
        <div class="metadata-item">
          <span class="metadata-label">Import ID:</span>
          <span class="metadata-value">{{ normalizedSummary.importId || 'N/A' }}</span>
        </div>
        <div class="metadata-item">
          <span class="metadata-label">Source File:</span>
          <span class="metadata-value">{{ bibFileName || 'Unknown' }}</span>
        </div>
        <div class="metadata-item">
          <span class="metadata-label">Workspace:</span>
          <span class="metadata-value">{{ workspace?.name || 'Unknown' }}</span>
        </div>
        <div class="metadata-item">
          <span class="metadata-label">Import Date:</span>
          <span class="metadata-value">{{ formatDate(new Date()) }}</span>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="summary-actions">
      <BaseButton
        variant="outline"
        @click="viewImportLog"
        class="action-button"
      >
        <BaseIcon icon-name="document" />
        View Import Log
      </BaseButton>

      <BaseButton
        variant="primary"
        @click="returnToLibrary"
        class="action-button primary-action"
      >
        <BaseIcon icon-name="external-link" />
        Return to Library
      </BaseButton>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/check";
import "assets/icons/info";
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/external-link";

import type { ImportResultSummary, TableColumn } from "./types";

interface FailedImportRow {
  reference: string;
  title: string;
  authors: string;
  error: string;
  actions: string;
}

export default {
  name: "ImportSummary",

  props: {
    normalizedSummary: {
      type: Object as () => ImportResultSummary,
      required: true,
    },
    workspace: {
      type: Object,
      default: null,
    },
    bibFileName: {
      type: String,
      default: "",
    },
    failedDocuments: {
      type: Array as () => any[],
      default: () => [],
    },
  },

  emits: ["retry-failed", "view-import-history", "return-to-library"],

  data() {
    return {
      isRetrying: false,
    };
  },

  computed: {
    hasSuccessfulImports(): boolean {
      return this.successfulCount > 0;
    },

    hasFailedImports(): boolean {
      return (this.normalizedSummary.failed || 0) > 0 && this.failedDocuments.length > 0;
    },

    successfulCount(): number {
      return (this.normalizedSummary.added || 0) + (this.normalizedSummary.updated || 0);
    },

    failedImportsTableData(): FailedImportRow[] {
      return this.failedDocuments.map((doc: any) => ({
        reference: doc.reference || 'Unknown',
        title: doc.title || 'Unknown Title',
        authors: this.formatAuthors(doc.authors),
        error: this.getErrorMessage(doc),
        actions: 'retry', // Placeholder for action buttons
      }));
    },

    failedImportsColumns(): TableColumn[] {
      return [
        {
          field: "reference",
          title: "Reference",
          width: 120,
          frozen: true,
          sortable: true,
        },
        {
          field: "title",
          title: "Title",
          minWidth: 200,
          sortable: true,
        },
        {
          field: "authors",
          title: "Authors",
          width: 180,
          sortable: true,
        },
        {
          field: "error",
          title: "Error Message",
          minWidth: 250,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="error-message" title="${value}">${value}</span>`;
          },
        },
        {
          field: "actions",
          title: "Actions",
          width: 100,
          frozen: true,
          sortable: false,
          formatter: () => {
            return '<button class="retry-button">Retry</button>';
          },
          cellClick: (e: Event, cell: any) => {
            e.preventDefault();
            const rowData = cell.getRow().getData();
            this.retryIndividualImport(rowData);
          },
        },
      ];
    },

    failedTableOptions() {
      return {
        height: "300px",
        pagination: "local",
        paginationSize: 10,
        paginationSizeSelector: [5, 10, 20],
        movableColumns: false,
        resizableRows: false,
        selectable: false,
        tooltips: true,
        layout: "fitColumns",
      };
    },
  },

  methods: {
    formatAuthors(authors: string | string[] | undefined): string {
      if (!authors) return 'Unknown Authors';
      if (Array.isArray(authors)) {
        return authors.slice(0, 3).join(', ') + (authors.length > 3 ? ' et al.' : '');
      }
      return String(authors);
    },

    getErrorMessage(doc: any): string {
      if (doc.validation_errors && doc.validation_errors.length > 0) {
        return doc.validation_errors[0];
      }
      if (doc.error) {
        return doc.error;
      }
      return 'Unknown error occurred during import';
    },

    formatDate(date: Date): string {
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    },

    async retryFailedImports() {
      if (this.isRetrying) return;

      this.isRetrying = true;
      try {
        this.$emit("retry-failed", this.failedDocuments);
      } finally {
        setTimeout(() => {
          this.isRetrying = false;
        }, 1000);
      }
    },

    async retryIndividualImport(rowData: FailedImportRow) {
      const failedDoc = this.failedDocuments.find(
        (doc: any) => doc.reference === rowData.reference
      );
      if (failedDoc) {
        this.$emit("retry-failed", [failedDoc]);
      }
    },

    viewImportLog() {
      this.$emit("view-import-history", {
        importId: this.normalizedSummary.importId,
        workspace: this.workspace,
      });
    },

    returnToLibrary() {
      this.$emit("return-to-library", {
        workspace: this.workspace,
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.import-summary {
  display: flex;
  flex-direction: column;
  gap: $base-space * 3;
  padding: $base-space * 3;
  height: 100%;
  overflow-y: auto;
}

// Summary header
.summary-header {
  text-align: center;
  padding: $base-space * 2;

  .summary-icon {
    font-size: 3rem;
    color: var(--color-success);
    margin-bottom: $base-space * 2;
  }

  h3 {
    margin: 0 0 $base-space 0;
    color: var(--fg-primary);
    font-size: 1.8rem;
    font-weight: 600;
  }

  .summary-subtitle {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
  }
}

// Import statistics
.import-statistics {
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: $base-space * 2;
    margin-bottom: $base-space * 2;

    .stat-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: $base-space * 2;
      background: var(--bg-solid-grey-2);
      border-radius: $border-radius;
      border: 1px solid var(--border-field);
      text-align: center;

      .stat-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: $base-space;
        color: var(--fg-primary);
      }

      .stat-label {
        font-size: 0.9rem;
        color: var(--fg-secondary);
        font-weight: 500;
      }

      &.stat-total .stat-value {
        color: var(--fg-primary);
      }

      &.stat-added .stat-value {
        color: var(--color-success);
      }

      &.stat-updated .stat-value {
        color: var(--bg-action);
      }

      &.stat-skipped .stat-value {
        color: var(--fg-secondary);
      }

      &.stat-failed .stat-value {
        color: var(--color-danger);
      }
    }
  }
}

// Results breakdown
.results-breakdown {
  h4 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1.3rem;
    font-weight: 600;
  }

  .result-section {
    padding: $base-space * 2;
    border-radius: $border-radius;
    border: 1px solid var(--border-field);
    margin-bottom: $base-space * 2;

    .section-header {
      display: flex;
      align-items: center;
      gap: $base-space;
      margin-bottom: $base-space;

      .section-icon {
        font-size: 1.2rem;
      }

      .section-title {
        font-weight: 600;
        color: var(--fg-primary);
        flex: 1;
      }

      .section-count {
        font-weight: 700;
        font-size: 1.1rem;
        padding: calc($base-space/2) $base-space;
        border-radius: $border-radius;
        background: var(--bg-solid-grey-3);
        color: var(--fg-primary);
      }
    }

    .section-description {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 0.9rem;
      line-height: 1.4;
    }

    &.success-section {
      background: var(--bg-banner-success);
      border-color: var(--color-success);

      .success-icon {
        color: var(--color-success);
      }

      .section-count {
        background: var(--color-success);
        color: white;
      }
    }

    &.skipped-section {
      background: var(--bg-solid-grey-2);
      border-color: var(--fg-secondary);

      .skipped-icon {
        color: var(--fg-secondary);
      }
    }

    &.failed-section {
      background: var(--bg-banner-error);
      border-color: var(--color-danger);

      .failed-icon {
        color: var(--color-danger);
      }

      .section-count {
        background: var(--color-danger);
        color: white;
      }
    }
  }
}

// Failed imports table
.failed-imports {
  h4 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1.3rem;
    font-weight: 600;
  }

  .failed-table-container {
    margin-bottom: $base-space * 2;
    border: 1px solid var(--border-field);
    border-radius: $border-radius;
    overflow: hidden;

    :deep(.failed-imports-table) {
      .error-message {
        display: block;
        max-width: 250px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .retry-button {
        padding: calc($base-space/2) $base-space;
        background: var(--bg-action);
        color: white;
        border: none;
        border-radius: $border-radius;
        font-size: 0.8rem;
        cursor: pointer;
        transition: background-color 0.2s ease;

        &:hover {
          background: var(--bg-action-hover);
        }
      }
    }
  }

  .retry-section {
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);

    .retry-description {
      margin: 0 0 $base-space * 2 0;
      color: var(--fg-secondary);
      font-size: 0.9rem;
      line-height: 1.4;
    }
  }
}

// Import metadata
.import-metadata {
  h4 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1.3rem;
    font-weight: 600;
  }

  .metadata-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: $base-space * 2;
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);

    .metadata-item {
      display: flex;
      flex-direction: column;
      gap: calc($base-space / 2);

      .metadata-label {
        font-size: 0.9rem;
        color: var(--fg-secondary);
        font-weight: 500;
      }

      .metadata-value {
        font-size: 1rem;
        color: var(--fg-primary);
        font-weight: 600;
        word-break: break-word;
      }
    }
  }
}

// Action buttons
.summary-actions {
  display: flex;
  gap: $base-space * 2;
  justify-content: center;
  padding-top: $base-space * 2;
  margin-top: auto;

  .action-button {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: $base-space * 1.5 $base-space * 2;
    font-size: 1rem;
    font-weight: 500;

    &.primary-action {
      min-width: 180px;
    }
  }
}

// Responsive design
@media (max-width: 768px) {
  .import-summary {
    padding: $base-space * 2;
  }

  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  }

  .metadata-grid {
    grid-template-columns: 1fr;
  }

  .summary-actions {
    flex-direction: column;
    align-items: stretch;

    .action-button {
      justify-content: center;
    }
  }
}
</style>