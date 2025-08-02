<template>
  <div class="import-history-list">
    <!-- Header -->
    <div class="history-header">
      <h3>Import History</h3>
      <p class="history-subtitle">
        View and manage all your document import operations
      </p>
    </div>

    <!-- Filters -->
    <div class="history-filters">
      <div class="filter-row">
        <div class="filter-group">
          <label class="filter-label">Search by filename:</label>
          <BaseInput
            v-model="filters.filename"
            placeholder="Enter filename..."
            class="filter-input"
            @input="debouncedSearch"
          />
        </div>

        <div class="filter-group">
          <label class="filter-label">Date range:</label>
          <div class="date-range">
            <BaseInput
              v-model="filters.date_from"
              type="date"
              placeholder="From date"
              class="filter-input date-input"
              @input="applyFilters"
            />
            <span class="date-separator">to</span>
            <BaseInput
              v-model="filters.date_to"
              type="date"
              placeholder="To date"
              class="filter-input date-input"
              @input="applyFilters"
            />
          </div>
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
      <p>Loading import history...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-container">
                  <BaseIcon icon-name="danger" class="error-icon" />
      <h4>Failed to Load Import History</h4>
      <p>{{ error }}</p>
      <BaseButton variant="outline" @click="loadHistory">
        Retry
      </BaseButton>
    </div>

    <!-- Empty State -->
    <div v-else-if="!historyData.items.length" class="empty-container">
              <BaseIcon icon-name="document" class="empty-icon" />
      <h4>No Import History Found</h4>
      <p v-if="hasActiveFilters">
        No imports match your current filters. Try adjusting your search criteria.
      </p>
      <p v-else>
        You haven't imported any documents yet. Start by importing your first bibliography file.
      </p>
    </div>

    <!-- History Table -->
    <div v-else class="history-table-container">
      <BaseSimpleTable
        :data="tableData"
        :columns="tableColumns"
        :options="tableOptions"
        class="history-table"
        @row-click="handleRowClick"
      />
    </div>

    <!-- Pagination -->
    <div v-if="historyData.pages > 1" class="pagination-container">
      <div class="pagination-info">
        Showing {{ startItem }} - {{ endItem }} of {{ historyData.total }} imports
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
          :disabled="currentPage >= historyData.pages"
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
import "assets/icons/danger";
import "assets/icons/document";
import "assets/icons/external-link";
import "assets/icons/time";

import type { TableColumn } from "./types";
import type {
  ImportHistoryListItem,
  ImportHistoryListResponse,
  ImportHistoryFilters,
} from "~/v1/domain/usecases/get-import-history-use-case";
import { useImportHistoryListViewModel } from "./useImportHistoryListViewModel";

interface HistoryTableRow {
  id: string;
  filename: string;
  uploaded_by: string;
  created_at: string;
  total_papers: number;
  success_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
  actions: string;
}

export default {
  name: "ImportHistoryList",

  props: {
    workspace: {
      type: Object,
      default: null,
    },
  },

  emits: ["view-details", "close"],

  setup(props) {
    return useImportHistoryListViewModel(props);
  },

  data() {
    return {
      // Data state
      historyData: {
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 0,
      } as ImportHistoryListResponse,

      // UI state
      isLoading: false,
      error: null as string | null,

      // Pagination
      currentPage: 1,
      pageSize: 20,

      // Filters
      filters: {
        filename: "",
        date_from: "",
        date_to: "",
      } as ImportHistoryFilters,

      // Search debouncing
      searchTimeout: null as NodeJS.Timeout | null,
    };
  },

  computed: {
    hasActiveFilters(): boolean {
      return this.hasActiveFiltersData(this.filters);
    },

    tableData(): HistoryTableRow[] {
      return this.transformToTableDataData(this.historyData.items);
    },

    tableColumns(): TableColumn[] {
      return [
        {
          field: "filename",
          title: "Source File",
          minWidth: 200,
          sortable: true,
          frozen: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="filename" title="${value}">${value}</span>`;
          },
        },
        {
          field: "uploaded_by",
          title: "Uploaded By",
          width: 150,
          sortable: true,
        },
        {
          field: "created_at",
          title: "Date & Time",
          width: 180,
          sortable: true,
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="date-time">${value}</span>`;
          },
        },
        {
          field: "total_papers",
          title: "Total Papers",
          width: 120,
          sortable: true,
          cssClass: "text-center",
        },
        {
          field: "success_count",
          title: "Success",
          width: 100,
          sortable: true,
          cssClass: "text-center",
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="status-success">${value}</span>`;
          },
        },
        {
          field: "updated_count",
          title: "Updated",
          width: 100,
          sortable: true,
          cssClass: "text-center",
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="status-updated">${value}</span>`;
          },
        },
        {
          field: "skipped_count",
          title: "Skipped",
          width: 100,
          sortable: true,
          cssClass: "text-center",
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="status-skipped">${value}</span>`;
          },
        },
        {
          field: "failed_count",
          title: "Failed",
          width: 100,
          sortable: true,
          cssClass: "text-center",
          formatter: (cell: any) => {
            const value = cell.getValue();
            return `<span class="status-failed">${value}</span>`;
          },
        },
        {
          field: "actions",
          title: "Actions",
          width: 120,
          sortable: false,
          frozen: true,
          formatter: () => {
            return '<button class="view-details-btn">View Details</button>';
          },
          cellClick: (e: Event, cell: any) => {
            e.preventDefault();
            const rowData = cell.getRow().getData();
            this.viewDetails(rowData);
          },
        },
      ];
    },

    tableOptions() {
      return {
        height: "400px",
        pagination: false, // We handle pagination manually
        movableColumns: false,
        resizableRows: false,
        selectable: false,
        tooltips: true,
        layout: "fitColumns",
        placeholder: "No import history found",
      };
    },

    startItem(): number {
      return this.calculateStartItemData(this.currentPage, this.pageSize);
    },

    endItem(): number {
      return this.calculateEndItemData(this.currentPage, this.pageSize, this.historyData.total);
    },

    visiblePages(): number[] {
      return this.calculateVisiblePagesData(this.currentPage, this.historyData.pages);
    },
  },

  async mounted() {
    await this.loadHistory();
  },

  beforeUnmount() {
    if (this.searchTimeout) {
      clearTimeout(this.searchTimeout);
    }
  },

  methods: {
    async loadHistory() {
      this.isLoading = true;
      this.error = null;

      try {
        const params = {
          page: this.currentPage,
          size: this.pageSize,
          sort_by: 'created_at',
          sort_order: 'desc' as const,
          filters: {
            ...this.filters,
            workspace_id: this.workspace?.id,
          },
        };

        this.historyData = await this.loadHistoryData(params);
      } catch (error: any) {
        console.error('Error loading import history:', error);
        this.error = error.message || 'Failed to load import history';
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
      await this.loadHistory();
    },

    async clearFilters() {
      this.filters = this.clearFiltersData();
      this.currentPage = 1;
      await this.loadHistory();
    },

    async goToPage(page: number) {
      if (page < 1 || page > this.historyData.pages) return;

      this.currentPage = page;
      await this.loadHistory();
    },

    handleRowClick(e: Event, row: any) {
      const rowData = row.getData();
      this.viewDetails(rowData);
    },

    viewDetails(rowData: HistoryTableRow) {
      this.handleRowClickData(rowData, this.$emit, this.workspace);
    },

    formatDate(dateString: string): string {
      return this.formatDateData(dateString);
    },

    close() {
      this.$emit("close");
    },
  },
};
</script>

<style lang="scss" scoped>
.import-history-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: $base-space * 3;
}

// Header
.history-header {
  margin-bottom: $base-space * 3;

  h3 {
    margin: 0 0 $base-space 0;
    color: var(--fg-primary);
    font-size: 1.5rem;
    font-weight: 600;
  }

  .history-subtitle {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
  }
}

// Filters
.history-filters {
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
      min-width: 200px;

      .filter-label {
        font-size: 0.9rem;
        color: var(--fg-secondary);
        font-weight: 500;
      }

      .filter-input {
        min-width: 180px;

        &.date-input {
          min-width: 140px;
        }
      }

      .date-range {
        display: flex;
        align-items: center;
        gap: $base-space;

        .date-separator {
          color: var(--fg-secondary);
          font-size: 0.9rem;
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

// Loading state
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;

  p {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
  }
}

// Error state
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;
  text-align: center;

  .error-icon {
    font-size: 3rem;
    color: var(--color-danger);
  }

  h4 {
    margin: 0;
    color: var(--color-danger);
    font-size: 1.3rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: var(--fg-primary);
    font-size: 1rem;
    max-width: 400px;
  }
}

// Empty state
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: $base-space * 2;
  text-align: center;

  .empty-icon {
    font-size: 3rem;
    color: var(--fg-secondary);
  }

  h4 {
    margin: 0;
    color: var(--fg-primary);
    font-size: 1.3rem;
    font-weight: 600;
  }

  p {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
    max-width: 400px;
    line-height: 1.4;
  }
}

// History table
.history-table-container {
  flex: 1;
  margin-bottom: $base-space * 2;
  border: 1px solid var(--border-field);
  border-radius: $border-radius;
  overflow: hidden;

  :deep(.history-table) {
    .filename {
      font-weight: 500;
      color: var(--fg-primary);
    }

    .date-time {
      font-size: 0.9rem;
      color: var(--fg-secondary);
    }

    .status-success {
      color: var(--color-success);
      font-weight: 600;
    }

    .status-updated {
      color: var(--bg-action);
      font-weight: 600;
    }

    .status-skipped {
      color: var(--fg-secondary);
      font-weight: 600;
    }

    .status-failed {
      color: var(--color-danger);
      font-weight: 600;
    }

    .view-details-btn {
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

// Pagination
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
  .import-history-list {
    padding: $base-space * 2;
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