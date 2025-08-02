<template>
  <div class="import-history-details">
    <!-- Header -->
    <div class="details-header">
      <div class="header-content">
        <div class="header-info">
          <h3>Import Details</h3>
          <p class="details-subtitle">
            {{ importDetails?.filename || 'Unknown File' }} -
            {{ formatDate(importDetails?.created_at) }}
          </p>
        </div>
        <div class="header-actions">
          <BaseButton
            variant="outline"
            @click="exportResults"
            :disabled="isExporting"
            class="export-btn"
          >
            <BaseIcon icon-name="export" />
            {{ isExporting ? 'Exporting...' : 'Export Results' }}
          </BaseButton>
          <BaseButton
            variant="outline"
            @click="close"
            class="close-btn"
          >
            <BaseIcon icon-name="close" />
            Close
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Summary Statistics -->
    <div v-if="importDetails" class="import-summary">
      <div class="summary-stats">
        <div class="stat-item stat-total">
          <span class="stat-value">{{ importDetails.summary.total_documents }}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="stat-item stat-added">
          <span class="stat-value">{{ importDetails.summary.add_count }}</span>
          <span class="stat-label">Added</span>
        </div>
        <div class="stat-item stat-updated">
          <span class="stat-value">{{ importDetails.summary.update_count }}</span>
          <span class="stat-label">Updated</span>
        </div>
        <div class="stat-item stat-skipped">
          <span class="stat-value">{{ importDetails.summary.skip_count }}</span>
          <span class="stat-label">Skipped</span>
        </div>
        <div class="stat-item stat-failed">
          <span class="stat-value">{{ importDetails.summary.failed_count }}</span>
          <span class="stat-label">Failed</span>
        </div>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="details-filters">
      <div class="filter-row">
        <div class="filter-group">
          <label class="filter-label">Search reference:</label>
          <BaseInput
            v-model="filters.reference"
            placeholder="Enter reference..."
            class="filter-input"
            @input="debouncedSearch"
          />
        </div>

        <div class="filter-group">
          <label class="filter-label">Search title:</label>
          <BaseInput
            v-model="filters.title"
            placeholder="Enter title..."
            class="filter-input"
            @input="debouncedSearch"
          />
        </div>

        <div class="filter-group">
          <label class="filter-label">Status:</label>
          <select
            v-model="filters.status"
            class="filter-select"
            @change="applyFilters"
          >
            <option value="">All Statuses</option>
            <option value="add">Added</option>
            <option value="update">Updated</option>
            <option value="skip">Skipped</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        <div class="filter-actions">
          <BaseButton
            variant="outline"
            @click="clearFilters"
            class="clear-filters-btn"
          >
            Clear Filters
          </BaseButton>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-container">
      <BaseSpinner />
      <p>Loading import details...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
              <BaseIcon icon-name="danger" class="error-icon" />
      <h4>Failed to Load Import Details</h4>
      <p>{{ error }}</p>
      <BaseButton variant="outline" @click="loadDetails">
        Retry
      </BaseButton>
    </div>

    <!-- Empty State -->
    <div v-else-if="!detailItems.length" class="empty-container">
              <BaseIcon icon-name="document" class="empty-icon" />
      <h4>No Details Found</h4>
      <p v-if="hasActiveFilters">
        No items match your current filters. Try adjusting your search criteria.
      </p>
      <p v-else>
        No detailed information available for this import.
      </p>
    </div>

    <!-- Details Table -->
    <div v-else class="details-table-container">
      <BaseSimpleTable
        :data="tableData"
        :columns="tableColumns"
        :options="tableOptions"
        class="details-table"
      />
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="pagination-container">
      <div class="pagination-info">
        Showing {{ startItem }} - {{ endItem }} of {{ totalItems }} items
      </div>
      <div class="pagination-controls">
        <BaseButton
          variant="outline"
          :disabled="currentPage <= 1"
          @click="goToPage(currentPage - 1)"
          class="pagination-btn"
        >
          Previous
        </BaseButton>

        <div class="page-numbers">
          <BaseButton
            v-for="page in visiblePages"
            :key="page"
            :variant="page === currentPage ? 'primary' : 'outline'"
            @click="goToPage(page)"
            class="page-btn"
          >
            {{ page }}
          </BaseButton>
        </div>

        <BaseButton
          variant="outline"
          :disabled="currentPage >= totalPages"
          @click="goToPage(currentPage + 1)"
          class="pagination-btn"
        >
          Next
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/export";
import "assets/icons/close";
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/check";
import "assets/icons/info";

import type { TableColumn } from "./types";
import type {
  ImportHistoryDetailItem,
  ImportHistoryDetailsResponse,
  ImportHistoryDetailsFilters,
} from "~/v1/domain/usecases/get-import-history-details-use-case";
import { useImportHistoryDetailsViewModel } from "./useImportHistoryDetailsViewModel";

interface DetailsTableRow {
  reference: string;
  title: string;
  authors: string;
  year: string;
  journal: string;
  status: string;
  associated_files: string;
  error_message: string;
  actions: string;
}

export default {
  name: "ImportHistoryDetails",

  props: {
    importId: {
      type: String,
      required: true,
    },
    filename: {
      type: String,
      default: "",
    },
    workspace: {
      type: Object,
      default: null,
    },
  },

  emits: ["close", "retry-item"],

  setup(props) {
    return useImportHistoryDetailsViewModel(props);
  },

  data() {
    return {
      // Data state
      importDetails: null as ImportHistoryDetailsResponse | null,
      detailItems: [] as ImportHistoryDetailItem[],

      // UI state
      isLoading: false,
      isExporting: false,
      error: null as string | null,

      // Pagination
      currentPage: 1,
      pageSize: 20,
      totalItems: 0,
      totalPages: 0,

      // Filters
      filters: {
        reference: "",
        title: "",
        authors: "",
        status: "",
        error_message: "",
      } as ImportHistoryDetailsFilters,

      // Search debouncing
      searchTimeout: null as NodeJS.Timeout | null,
    };
  },

  computed: {
    hasActiveFilters(): boolean {
      return this.hasActiveFiltersData(this.filters);
    },

    tableData(): DetailsTableRow[] {
      return this.transformToTableDataData(this.detailItems);
    },

    tableColumns(): TableColumn[] {
      return [
        {
          field: "reference",
          title: "Reference",
          width: 120,
          frozen: true,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="reference-cell" title="${value}">${value}</span>`;
          },
        },
        {
          field: "title",
          title: "Title",
          minWidth: 250,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="title-cell" title="${value}">${this.truncateText(value, 60)}</span>`;
          },
        },
        {
          field: "authors",
          title: "Authors",
          width: 180,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="authors-cell" title="${value}">${this.truncateText(value, 30)}</span>`;
          },
        },
        {
          field: "year",
          title: "Year",
          width: 80,
          sortable: true,
          cssClass: "text-center",
        },
        {
          field: "journal",
          title: "Journal",
          width: 150,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="journal-cell" title="${value}">${this.truncateText(value, 20)}</span>`;
          },
        },
        {
          field: "status",
          title: "Status",
          width: 100,
          sortable: true,
          cssClass: "text-center",
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="status-badge status-${value}">${this.formatStatus(value)}</span>`;
          },
        },
        {
          field: "associated_files",
          title: "Files",
          width: 150,
          sortable: false,
          formatter: (cell: any) => {
            const value = cell.getValue();
            if (!value || value === 'None') {
              return '<span class="no-files">No files</span>';
            }
            const files = value.split(', ');
            const displayText = files.length > 1 ? `${files.length} files` : files[0];
            return `<span class="files-cell" title="${value}">${displayText}</span>`;
          },
        },
        {
          field: "error_message",
          title: "Error",
          width: 200,
          sortable: false,
          formatter: (cell: any) => {
            const value = cell.getValue();
            if (!value || value === 'None') {
              return '<span class="no-error">-</span>';
            }
            return `<span class="error-cell" title="${value}">${this.truncateText(value, 30)}</span>`;
          },
        },
        {
          field: "actions",
          title: "Actions",
          width: 100,
          sortable: false,
          frozen: true,
          formatter: (cell: any) => {
            const rowData = cell.getRow().getData();
            if (rowData.status === 'failed') {
              return '<button class="retry-btn">Retry</button>';
            }
            return '<span class="no-actions">-</span>';
          },
          cellClick: (e: Event, cell: any) => {
            e.preventDefault();
            const rowData = cell.getRow().getData();
            if (rowData.status === 'failed') {
              this.retryItem(rowData);
            }
          },
        },
      ];
    },

    tableOptions() {
      return {
        height: "500px",
        pagination: false, // We handle pagination manually
        movableColumns: false,
        resizableRows: false,
        selectable: false,
        tooltips: true,
        layout: "fitColumns",
        placeholder: "No import details found",
      };
    },

    startItem(): number {
      return this.calculateStartItemData(this.currentPage, this.pageSize);
    },

    endItem(): number {
      return this.calculateEndItemData(this.currentPage, this.pageSize, this.totalItems);
    },

    visiblePages(): number[] {
      return this.calculateVisiblePagesData(this.currentPage, this.totalPages);
    },
  },

  async mounted() {
    await this.loadDetails();
  },

  beforeUnmount() {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
  },

  methods: {
    async loadDetails() {
      this.isLoading = true;
      this.error = null;

      try {
        const params = {
          page: this.currentPage,
          size: this.pageSize,
          sort_by: 'reference',
          sort_order: 'asc' as const,
          filters: this.filters,
        };

        const result = await this.loadDetailsData(this.importId, params);

        this.importDetails = result.details;
        this.detailItems = result.items;
        this.totalItems = result.total;
        this.totalPages = result.pages;
      } catch (error: any) {
        console.error('Error loading import details:', error);
        this.error = error.message || 'Failed to load import details';
      } finally {
        this.isLoading = false;
      }
    },

    debouncedSearch() {
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout);
      }

      this.searchTimeout = setTimeout(() => {
        this.applyFilters();
      }, 500);
    },

    async applyFilters() {
      this.currentPage = 1; // Reset to first page when filtering
      await this.loadDetails();
    },

    async clearFilters() {
      this.filters = this.clearFiltersData();
      this.currentPage = 1;
      await this.loadDetails();
    },

    async goToPage(page: number) {
      if (page < 1 || page > this.totalPages) return;

      this.currentPage = page;
      await this.loadDetails();
    },

    async exportResults() {
      if (this.isExporting) return;

      this.isExporting = true;
      try {
        const csvContent = this.createCSVContentData(this.detailItems);
        const filename = `import-details-${this.importId}.csv`;

        this.downloadCSVData(csvContent, filename);
      } catch (error) {
        console.error('Error exporting results:', error);
        // Could show a toast notification here
      } finally {
        setTimeout(() => {
          this.isExporting = false;
        }, 1000);
      }
    },

    retryItem(rowData: DetailsTableRow) {
      const item = this.detailItems.find(item => item.reference === rowData.reference);
      if (item) {
        this.$emit("retry-item", item);
      }
    },

    formatDate(dateString: string | undefined): string {
      return this.formatDateData(dateString);
    },

    formatStatus(status: string): string {
      return this.formatStatusData(status);
    },

    truncateText(text: string, maxLength: number): string {
      return this.truncateTextData(text, maxLength);
    },

    close() {
      this.$emit("close");
    },
  },
};
</script>

<style lang="scss" scoped>
.import-history-details {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: $base-space * 3;
}

// Header
.details-header {
  margin-bottom: $base-space * 3;

  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: start;
    gap: $base-space * 2;

    .header-info {
      flex: 1;

      h3 {
        margin: 0 0 $base-space 0;
        color: var(--fg-primary);
        font-size: 1.5rem;
        font-weight: 600;
      }

      .details-subtitle {
        margin: 0;
        color: var(--fg-secondary);
        font-size: 1rem;
      }
    }

    .header-actions {
      display: flex;
      gap: $base-space;

      .export-btn,
      .close-btn {
        display: flex;
        align-items: center;
        gap: calc($base-space / 2);
        white-space: nowrap;
      }
    }
  }
}

// Summary statistics
.import-summary {
  margin-bottom: $base-space * 3;

  .summary-stats {
    display: flex;
    gap: $base-space * 2;
    padding: $base-space * 2;
    background: var(--bg-solid-grey-2);
    border-radius: $border-radius;
    border: 1px solid var(--border-field);

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      min-width: 80px;

      .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: calc($base-space / 2);
        color: var(--fg-primary);
      }

      .stat-label {
        font-size: 0.8rem;
        color: var(--fg-secondary);
        font-weight: 500;
        text-transform: uppercase;
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

// Filters
.details-filters {
  margin-bottom: $base-space * 3;
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  .filter-row {
    display: flex;
    gap: $base-space * 2;
    align-items: end;
    flex-wrap: wrap;

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: calc($base-space / 2);
      min-width: 180px;

      .filter-label {
        font-size: 0.9rem;
        color: var(--fg-secondary);
        font-weight: 500;
      }

      .filter-input {
        min-width: 160px;
      }

      .filter-select {
        padding: $base-space;
        border: 1px solid var(--border-field);
        border-radius: $border-radius;
        background: var(--bg-solid-grey-1);
        color: var(--fg-primary);
        font-size: 0.9rem;
        min-width: 140px;

        &:focus {
          outline: none;
          border-color: var(--bg-action);
        }
      }
    }

    .filter-actions {
      display: flex;
      align-items: end;
      margin-left: auto;

      .clear-filters-btn {
        white-space: nowrap;
      }
    }
  }
}

// Loading, error, empty states (same as ImportHistoryList)
.loading-container,
.error-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;
  text-align: center;

  .error-icon,
  .empty-icon {
    font-size: 3rem;
  }

  .error-icon {
    color: var(--color-danger);
  }

  .empty-icon {
    color: var(--fg-secondary);
  }

  h4 {
    margin: 0;
    font-size: 1.3rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    font-size: 1rem;
    max-width: 400px;
    line-height: 1.4;
  }
}

.error-container h4 {
  color: var(--color-danger);
}

.empty-container h4 {
  color: var(--fg-primary);
}

.loading-container p,
.empty-container p {
  color: var(--fg-secondary);
}

.error-container p {
  color: var(--fg-primary);
}

// Details table
.details-table-container {
  flex: 1;
  margin-bottom: $base-space * 2;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  overflow: hidden;

  :deep(.details-table) {
    .reference-cell {
      font-weight: 600;
      color: var(--fg-primary);
    }

    .title-cell {
      color: var(--fg-primary);
      line-height: 1.3;
    }

    .authors-cell,
    .journal-cell {
      color: var(--fg-secondary);
      font-size: 0.9rem;
    }

    .status-badge {
      padding: calc($base-space/4) calc($base-space / 2);
      border-radius: $border-radius;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;

      &.status-add {
        background: var(--color-success);
        color: white;
      }

      &.status-update {
        background: var(--bg-action);
        color: white;
      }

      &.status-skip {
        background: var(--fg-secondary);
        color: white;
      }

      &.status-failed {
        background: var(--color-danger);
        color: white;
      }
    }

    .files-cell {
      color: var(--fg-primary);
      font-size: 0.9rem;
    }

    .no-files,
    .no-error,
    .no-actions {
      color: var(--fg-secondary);
      font-style: italic;
    }

    .error-cell {
      color: var(--color-danger);
      font-size: 0.9rem;
    }

    .retry-btn {
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

    .text-center {
      text-align: center;
    }
  }
}

// Pagination (same as ImportHistoryList)
.pagination-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  .pagination-info {
    color: var(--fg-secondary);
    font-size: 0.9rem;
  }

  .pagination-controls {
    display: flex;
    align-items: center;
    gap: $base-space;

    .pagination-btn {
      padding: calc($base-space/2) $base-space;
      font-size: 0.9rem;
    }

    .page-numbers {
      display: flex;
      gap: calc($base-space / 2);

      .page-btn {
        padding: calc($base-space/2) $base-space;
        font-size: 0.9rem;
        min-width: 36px;
        text-align: center;
      }
    }
  }
}

// Responsive design
@media (max-width: 768px) {
  .import-history-details {
    padding: $base-space * 2;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;

    .header-actions {
      justify-content: flex-end;
    }
  }

  .summary-stats {
    flex-wrap: wrap;
    justify-content: center;
  }

  .filter-row {
    flex-direction: column;
    align-items: stretch;

    .filter-group {
      min-width: auto;
    }

    .filter-actions {
      margin-left: 0;
      margin-top: $base-space;
    }
  }

  .pagination-container {
    flex-direction: column;
    gap: $base-space * 2;
    text-align: center;

    .pagination-controls {
      justify-content: center;
    }
  }
}
</style>