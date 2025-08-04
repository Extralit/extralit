<template>
  <div class="import-history-data-preview">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <BaseSpinner />
      <p>Loading import data...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="hasError" class="error-state">
      <BaseIcon icon-name="danger" class="error-icon" />
      <div class="error-content">
        <h4>Failed to Load Data</h4>
        <p>{{ errorMessage }}</p>
        <BaseButton variant="outline" @click="$emit('retry')">
          Retry
        </BaseButton>
      </div>
    </div>

    <!-- Main content -->
    <div v-else-if="importHistoryDetails" class="preview-content">
      <!-- Header with summary -->
      <div class="preview-header">
        <div class="header-info">
          <h3>{{ importHistoryDetails.filename }}</h3>
          <p class="subtitle">
            {{ totalRecords }} records imported on {{ formatDate(importHistoryDetails.createdAt) }}
          </p>
        </div>
        <div class="summary-stats">
          <div class="stat-item stat-total">
            <span class="stat-label">Total:</span>
            <span class="stat-value">{{ summary.total_documents }}</span>
          </div>
          <div class="stat-item stat-success">
            <span class="stat-label">Success:</span>
            <span class="stat-value">{{ summary.add_count + summary.update_count }}</span>
          </div>
          <div v-if="summary.failed_count > 0" class="stat-item stat-failed">
            <span class="stat-label">Failed:</span>
            <span class="stat-value">{{ summary.failed_count }}</span>
          </div>
        </div>
      </div>

      <!-- Search and filters -->
      <div class="preview-controls">
        <div class="search-section">
          <BaseInput
            v-model="searchQuery"
            placeholder="Search records..."
            class="search-input"
          >
            <template #prepend>
              <BaseIcon icon-name="search" />
            </template>
          </BaseInput>
        </div>
        <div class="filter-section">
          <select v-model="statusFilter" class="status-filter">
            <option value="">All Status</option>
            <option value="add">Add</option>
            <option value="update">Update</option>
            <option value="skip">Skip</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      <!-- Data table -->
      <div class="table-container">
        <BaseSimpleTable
          :data="filteredData"
          :columns="tableColumns"
          :options="tableOptions"
          :loading="loading"
          @row-click="handleRowClick"
        />
      </div>

      <!-- Pagination info -->
      <div v-if="showPaginationInfo" class="pagination-info">
        <p>
          Showing {{ Math.min(currentPage * pageSize, filteredData.length) }} of {{ filteredData.length }} records
          <span v-if="searchQuery || statusFilter">(filtered from {{ totalRecords }} total)</span>
        </p>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <BaseIcon icon-name="document" />
      <h4>No Import Data</h4>
      <p>No import history data available to preview.</p>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/search";
import "assets/icons/check";
import "assets/icons/close";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

interface TableColumn {
  field: string;
  title: string;
  width?: number;
  minWidth?: number;
  maxWidth?: number;
  formatter?: (cell: any) => string;
  filterable?: boolean;
  headerFilter?: string;
  frozen?: boolean;
  sortable?: boolean;
}

interface PreviewRecord extends Record<string, any> {
  reference: string;
  status: string;
  _metadata?: any;
}

export default {
  name: "ImportHistoryDataPreview",

  props: {
    importHistoryDetails: {
      type: ImportHistoryDetails,
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    error: {
      type: String,
      default: null,
    },
    maxHeight: {
      type: String,
      default: "500px",
    },
    showPaginationInfo: {
      type: Boolean,
      default: true,
    },
  },

  emits: ["retry", "row-selected", "field-selected"],

  data() {
    return {
      searchQuery: "",
      statusFilter: "",
      currentPage: 1,
      pageSize: 20,
    };
  },

  computed: {
    hasError(): boolean {
      return !!this.error;
    },

    errorMessage(): string {
      return this.error || "An unknown error occurred";
    },

    totalRecords(): number {
      return this.importHistoryDetails?.records?.length || 0;
    },

    summary() {
      return this.importHistoryDetails?.summary || {
        total_documents: 0,
        add_count: 0,
        update_count: 0,
        skip_count: 0,
        failed_count: 0,
      };
    },

    tableData(): PreviewRecord[] {
      if (!this.importHistoryDetails?.records) {
        return [];
      }

      return this.importHistoryDetails.records.map((record: Record<string, any>) => {
        const reference = record.reference || record.id || `record_${Math.random()}`;
        const metadata = this.importHistoryDetails.metadata[reference] || {};

        return {
          ...record,
          reference,
          status: metadata.status || "add",
          _metadata: metadata,
        };
      });
    },

    filteredData(): PreviewRecord[] {
      let data = [...this.tableData];

      // Apply search filter
      if (this.searchQuery.trim()) {
        const query = this.searchQuery.toLowerCase().trim();
        data = data.filter((record) => {
          return Object.values(record).some((value) => {
            if (value == null) return false;
            return String(value).toLowerCase().includes(query);
          });
        });
      }

      // Apply status filter
      if (this.statusFilter) {
        data = data.filter((record) => record.status === this.statusFilter);
      }

      return data;
    },

    tableColumns(): TableColumn[] {
      if (!this.importHistoryDetails?.schema?.fields) {
        return [];
      }

      const columns: TableColumn[] = [];

      // Add reference column first (frozen)
      columns.push({
        field: "reference",
        title: "Reference",
        width: 150,
        frozen: true,
        formatter: this.referenceFormatter,
        filterable: true,
        headerFilter: "input",
      });

      // Add dynamic columns from schema
      this.importHistoryDetails.schema.fields.forEach((field: any) => {
        if (field.name === "reference") return; // Skip reference as it's already added

        const column: TableColumn = {
          field: field.name,
          title: this.formatColumnTitle(field.name),
          width: this.getColumnWidth(field.name, field.type),
          formatter: this.getColumnFormatter(field.name, field.type),
          filterable: true,
          headerFilter: field.type === "string" ? "input" : undefined,
        };

        // Special handling for common fields
        if (field.name === "title") {
          column.width = 300;
          column.formatter = this.titleFormatter;
        } else if (field.name === "authors" || field.name === "author") {
          column.width = 200;
          column.formatter = this.authorsFormatter;
        } else if (field.name === "year") {
          column.width = 80;
        } else if (field.name === "doi") {
          column.width = 120;
          column.formatter = this.doiFormatter;
        }

        columns.push(column);
      });

      // Add status column at the end (frozen)
      columns.push({
        field: "status",
        title: "Status",
        width: 120,
        frozen: true,
        formatter: this.statusFormatter,
        filterable: true,
        headerFilter: "select",
      });

      return columns;
    },

    tableOptions() {
      return {
        layout: "fitData",
        maxHeight: this.maxHeight,
        pagination: true,
        paginationSize: this.pageSize,
        paginationSizeSelector: [10, 20, 50, 100],
        sortMode: "local",
        filterMode: "local",
        placeholder: "No records found",
        renderHorizontal: "virtual",
        resizableColumns: true,
        movableColumns: false,
        selectable: false,
        tooltipsHeader: true,
        tooltips: true,
      };
    },
  },

  watch: {
    searchQuery() {
      this.currentPage = 1;
    },
    statusFilter() {
      this.currentPage = 1;
    },
  },

  methods: {
    formatDate(date: Date | string): string {
      const dateObj = typeof date === 'string' ? new Date(date) : date;
      return dateObj.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },

    formatColumnTitle(fieldName: string): string {
      return fieldName
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (str) => str.toUpperCase())
        .trim();
    },

    getColumnWidth(fieldName: string, fieldType: string): number {
      // Default widths based on field type and name
      if (fieldType === "boolean") return 80;
      if (fieldType === "integer" || fieldType === "float") return 100;
      if (fieldName.includes("id") || fieldName.includes("key")) return 120;
      if (fieldName.includes("url") || fieldName.includes("link")) return 200;
      return 150; // Default width
    },

    getColumnFormatter(fieldName: string, fieldType: string) {
      if (fieldType === "boolean") return this.booleanFormatter;
      if (fieldType === "integer" || fieldType === "float") return this.numberFormatter;
      if (fieldName.includes("url") || fieldName.includes("link")) return this.urlFormatter;
      return undefined; // Use default formatter
    },

    // Cell formatters
    referenceFormatter(cell: any): string {
      const value = cell.getValue();
      return `<span class="reference-cell">${value}</span>`;
    },

    titleFormatter(cell: any): string {
      const value = cell.getValue() || "Untitled";
      const truncated = value.length > 60 ? value.substring(0, 60) + "..." : value;
      return `<span class="title-cell" title="${value}">${truncated}</span>`;
    },

    authorsFormatter(cell: any): string {
      const value = cell.getValue();
      if (!value) return '<span class="authors-cell">Unknown Authors</span>';

      let authors = value;
      if (Array.isArray(value)) {
        authors = value.slice(0, 3).join(", ");
        if (value.length > 3) authors += " et al.";
      } else if (typeof value === "string" && value.includes(",")) {
        const authorList = value.split(",").map(a => a.trim());
        authors = authorList.slice(0, 3).join(", ");
        if (authorList.length > 3) authors += " et al.";
      }

      return `<span class="authors-cell" title="${value}">${authors}</span>`;
    },

    doiFormatter(cell: any): string {
      const value = cell.getValue();
      if (!value) return "";

      const doiUrl = value.startsWith("http") ? value : `https://doi.org/${value}`;
      return `<a href="${doiUrl}" target="_blank" class="doi-link" title="Open DOI">${value}</a>`;
    },

    statusFormatter(cell: any): string {
      const status = cell.getValue();
      const statusClass = `status-${status}`;
      const statusText = this.getStatusText(status);

      return `
        <div class="status-cell ${statusClass}">
          <span class="status-indicator"></span>
          <span class="status-text">${statusText}</span>
        </div>
      `;
    },

    booleanFormatter(cell: any): string {
      const value = cell.getValue();
      const icon = value ? "check" : "close";
      const className = value ? "boolean-true" : "boolean-false";
      return `<span class="boolean-cell ${className}"><BaseIcon icon-name="${icon}" /></span>`;
    },

    numberFormatter(cell: any): string {
      const value = cell.getValue();
      if (value == null) return "";
      return `<span class="number-cell">${Number(value).toLocaleString()}</span>`;
    },

    urlFormatter(cell: any): string {
      const value = cell.getValue();
      if (!value) return "";

      const displayText = value.length > 30 ? value.substring(0, 30) + "..." : value;
      return `<a href="${value}" target="_blank" class="url-link" title="${value}">${displayText}</a>`;
    },

    getStatusText(status: string): string {
      const statusMap: Record<string, string> = {
        add: "Add",
        update: "Update",
        skip: "Skip",
        failed: "Failed",
      };
      return statusMap[status] || status;
    },

    handleRowClick(_event: any, row: any): void {
      const rowData = row.getData();
      this.$emit("row-selected", rowData);
    },

    // Public methods for parent components
    clearFilters(): void {
      this.searchQuery = "";
      this.statusFilter = "";
    },

    exportData(): PreviewRecord[] {
      return this.filteredData;
    },

    getFieldStats(fieldName: string) {
      if (!this.importHistoryDetails) return null;
      return this.importHistoryDetails.getFieldStats(fieldName);
    },
  },
};
</script>

<style lang="scss" scoped>
.import-history-data-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
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

// Empty state
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: $base-space * 2;
  color: var(--fg-secondary);

  h4 {
    margin: 0;
    color: var(--fg-primary);
    font-weight: 600;
  }

  p {
    margin: 0;
    font-size: 0.9rem;
  }
}

// Main content
.preview-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: $base-space * 2;
}

// Header
.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  @include media("<tablet") {
    flex-direction: column;
    gap: $base-space * 2;
  }

  .header-info {
    h3 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
      font-size: 1.2rem;
      font-weight: 600;
    }

    .subtitle {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 0.9rem;
    }
  }

  .summary-stats {
    display: flex;
    gap: $base-space * 2;
    flex-wrap: wrap;

    @include media("<tablet") {
      justify-content: flex-start;
    }

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

      &.stat-total .stat-value {
        color: var(--fg-primary);
      }

      &.stat-success .stat-value {
        color: var(--color-success);
      }

      &.stat-failed .stat-value {
        color: var(--color-danger);
      }
    }
  }
}

// Controls
.preview-controls {
  display: flex;
  gap: $base-space * 2;
  align-items: center;
  padding: 0 $base-space;

  @include media("<tablet") {
    flex-direction: column;
    align-items: stretch;
  }

  .search-section {
    flex: 1;
    max-width: 300px;

    @include media("<tablet") {
      max-width: none;
    }

    .search-input {
      width: 100%;
    }
  }

  .filter-section {
    .status-filter {
      padding: $base-space;
      border: 1px solid var(--border-field);
      border-radius: $border-radius-s;
      background: var(--bg-accent-grey-1);
      color: var(--fg-primary);
      font-size: 0.9rem;
      min-width: 120px;

      &:focus {
        border-color: var(--bg-action);
        outline: none;
      }
    }
  }
}

// Table container
.table-container {
  flex: 1;
  min-height: 300px;
  border-radius: $border-radius;
  overflow: hidden;
}

// Pagination info
.pagination-info {
  padding: $base-space;
  text-align: center;
  color: var(--fg-secondary);
  font-size: 0.9rem;
  border-top: 1px solid var(--border-field);
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
    cursor: help;
  }

  .authors-cell {
    color: var(--fg-secondary);
    font-size: 0.9rem;
    cursor: help;
  }

  .doi-link,
  .url-link {
    color: var(--bg-action);
    text-decoration: none;

    &:hover {
      text-decoration: underline;
    }
  }

  .boolean-cell {
    display: flex;
    justify-content: center;
    align-items: center;

    &.boolean-true {
      color: var(--color-success);
    }

    &.boolean-false {
      color: var(--fg-tertiary);
    }
  }

  .number-cell {
    text-align: right;
    font-family: $quaternary-font-family;
  }

  .status-cell {
    display: flex;
    align-items: center;
    gap: $base-space;
    padding: 4px 8px;
    border-radius: $border-radius-s;
    font-weight: 500;
    font-size: 0.9rem;

    .status-indicator {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
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