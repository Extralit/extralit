<template>
  <div class="import-history-list">
    <!-- Header -->
    <div class="history-header">
      <h3>Import History</h3>
      <p class="history-subtitle">
        View and manage all your document import operations
      </p>
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
      <p>
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

import type { TableColumn } from "../types";
import type {
  ImportHistoryListItem,
  ImportHistoryListResponse,
} from "~/v1/domain/usecases/get-import-history-use-case";
import { useImportHistoryListViewModel } from "./useImportHistoryListViewModel";

interface HistoryTableRow {
  id: string;
  filename: string;
  username: string;
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
    };
  },

  computed: {
    tableData(): HistoryTableRow[] {
      return this.transformToTableData(this.historyData.items);
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
          field: "username",
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
      return (this.currentPage - 1) * this.pageSize + 1;
    },

    endItem(): number {
      return Math.min(this.currentPage * this.pageSize, this.historyData.total);
    },

    visiblePages(): number[] {
      const delta = 2;
      let start = Math.max(1, this.currentPage - delta);
      let end = Math.min(this.historyData.pages, this.currentPage + delta);

      // Adjust if we're near the beginning or end
      if (end - start < 2 * delta) {
        if (start === 1) {
          end = Math.min(this.historyData.pages, start + 2 * delta);
        } else if (end === this.historyData.pages) {
          start = Math.max(1, end - 2 * delta);
        }
      }

      const pages = [];
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },
  },

  async mounted() {
    await this.loadHistory();
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
            workspace_id: this.workspace?.id,
          },
        };

        this.historyData = await this.getImportHistoryUseCase.execute(params);
      } catch (error: any) {
        console.error('Error loading import history:', error);
        this.error = error.message || 'Failed to load import history';
      } finally {
        this.isLoading = false;
      }
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
      this.$emit("view-details", {
        importId: rowData.id,
        filename: rowData.filename,
        workspace: this.workspace,
      });
    },

    formatDate(dateString: string): string {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },

    transformToTableData(items: ImportHistoryListItem[]): HistoryTableRow[] {
      return items.map((item: ImportHistoryListItem) => ({
        id: item.id,
        filename: item.filename,
        username: item.username || "Unknown User",
        created_at: this.formatDate(item.created_at),
        total_papers: item.total_papers,
        success_count: item.success_count,
        updated_count: item.updated_count,
        skipped_count: item.skipped_count,
        failed_count: item.failed_count,
        actions: "view-details",
      }));
    },

    close() {
      this.$emit("close");
    },
  },

  setup(props) {
    return useImportHistoryListViewModel(props);
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