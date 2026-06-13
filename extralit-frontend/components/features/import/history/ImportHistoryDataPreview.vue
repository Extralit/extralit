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
          <span class="subtitle">
            {{ totalRecords }} references imported on {{ formatDate(importHistoryDetails.createdAt) }}
          </span>
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
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

interface ColumnComponent {
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

    tableColumns(): ColumnComponent[] {
      if (!this.importHistoryDetails?.schema?.fields) {
        return [];
      }

      const columns: ColumnComponent[] = [];

      // Add reference column first (frozen)
      columns.push({
        field: "reference",
        title: "reference",
        width: 150,
        frozen: true,
        formatter: this.referenceFormatter,
      });

      // Add dynamic columns from schema
      this.importHistoryDetails.schema.fields.forEach((field: any) => {
        if (field.name === "reference") return; // Skip reference as it's already added

        const column: ColumnComponent = {
          field: field.name,
          title: this.formatColumnTitle(field.name),
          width: this.getColumnWidth(field.name, field.type),
          formatter: this.getColumnFormatter(field.name, field.type),
        };

        columns.push(column);
      });

      return columns;
    },

    tableOptions() {
      return {
        layout: "fitDataFill",
        maxHeight: "100%",
        pagination: this.filteredData.length > 20 ? true : false,
        sortMode: "local",
        placeholder: "No records found",
        renderVerticalBuffer: 300,
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
      if (!date) {
        return "Unknown date";
      }

      try {
        const dateObj = typeof date === 'string' ? new Date(date) : date;

        // Check if the date is valid
        if (isNaN(dateObj.getTime())) {
          return "Invalid date";
        }

        return dateObj.toLocaleDateString("en-US", {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
      } catch (error) {
        console.error("Error formatting date:", error);
        return "Date formatting error";
      }
    },

    formatColumnTitle(fieldName: string): string {
      return fieldName
        .replace(/([A-Z])/g, " $1")
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

    booleanFormatter(cell: any): string {
      const value = cell.getValue();
      const boolValue = Boolean(value);
      return `<span class="boolean-cell boolean-${boolValue}">${boolValue ? '✓' : '✗'}</span>`;
    },

    numberFormatter(cell: any): string {
      const value = cell.getValue();
      if (value == null || value === '') return '-';
      return `<span class="number-cell">${Number(value).toLocaleString()}</span>`;
    },

    urlFormatter(cell: any): string {
      const value = cell.getValue();
      if (!value || typeof value !== 'string') return '-';
      return `<a href="${value}" target="_blank" class="url-link">${value}</a>`;
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
  gap: $base-space;
  flex: 1;
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
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;

    h3 {
      margin: 0;
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

}

// Controls

// Table container
.table-container {
  flex: 1;
  min-height: 300px;
  border-radius: $border-radius;
  overflow: auto;
  width: 100%;
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