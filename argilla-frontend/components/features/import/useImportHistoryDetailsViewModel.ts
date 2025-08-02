/**
 * View model for ImportHistoryDetails component
 * Handles loading, filtering, and pagination of import history details
 */

import { useResolve } from "ts-injecty";
import type {
  ImportHistoryDetailItem,
  ImportHistoryDetailsResponse,
  ImportHistoryDetailsFilters,
} from "~/v1/domain/usecases/get-import-history-details-use-case";
import { GetImportHistoryDetailsUseCase } from "~/v1/domain/usecases/get-import-history-details-use-case";

interface LoadDetailsParams {
  page: number;
  size: number;
  sort_by: string;
  sort_order: "asc" | "desc";
  filters: ImportHistoryDetailsFilters;
}

export function useImportHistoryDetailsViewModel(props: any) {
  const getImportHistoryDetailsUseCase = useResolve(GetImportHistoryDetailsUseCase);

  return {
    // Use case
    getImportHistoryDetailsUseCase,

    // Main data loading method
    async loadDetailsData(
      importId: string,
      params: LoadDetailsParams
    ): Promise<{
      details: ImportHistoryDetailsResponse;
      items: ImportHistoryDetailItem[];
      total: number;
      pages: number;
    }> {
      const result = await getImportHistoryDetailsUseCase.execute(importId, params);

      return {
        details: result.details,
        items: result.items,
        total: result.total,
        pages: result.pages,
      };
    },

    // Filter helpers
    hasActiveFiltersData(filters: ImportHistoryDetailsFilters): boolean {
      return !!(filters.reference || filters.title || filters.authors || filters.status || filters.error_message);
    },

    clearFiltersData(): ImportHistoryDetailsFilters {
      return {
        reference: "",
        title: "",
        authors: "",
        status: "",
        error_message: "",
      };
    },

    // Pagination helpers
    calculateStartItemData(currentPage: number, pageSize: number): number {
      return (currentPage - 1) * pageSize + 1;
    },

    calculateEndItemData(currentPage: number, pageSize: number, totalItems: number): number {
      return Math.min(currentPage * pageSize, totalItems);
    },

    calculateVisiblePagesData(currentPage: number, totalPages: number, delta = 2): number[] {
      let start = Math.max(1, currentPage - delta);
      let end = Math.min(totalPages, currentPage + delta);

      if (end - start < 2 * delta) {
        if (start === 1) {
          end = Math.min(totalPages, start + 2 * delta);
        } else if (end === totalPages) {
          start = Math.max(1, end - 2 * delta);
        }
      }

      const pages = [];
      for (let i = start; i <= end; i++) {
        pages.push(i);
      }
      return pages;
    },

    // Export helpers
    createCSVContentData(items: ImportHistoryDetailItem[]): string {
      const headers = [
        "Reference",
        "Title",
        "Authors",
        "Year",
        "Journal",
        "Status",
        "Associated Files",
        "Error Message",
      ];

      const rows = items.map((item) => [
        item.reference,
        item.title,
        item.authors,
        item.year,
        item.journal || "",
        item.status,
        item.associated_files.join("; "),
        item.error_message || "",
      ]);

      const csvRows = [headers, ...rows];

      return csvRows.map((row) => row.map((field) => `"${String(field).replace(/"/g, "\"\"")}"`).join(",")).join("\n");
    },

    downloadCSVData(csvContent: string, filename: string): void {
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const link = document.createElement("a");
      const url = URL.createObjectURL(blob);

      link.setAttribute("href", url);
      link.setAttribute("download", filename);
      link.style.visibility = "hidden";

      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      URL.revokeObjectURL(url);
    },

    // Formatting helpers
    formatDateData(dateString: string | undefined): string {
      if (!dateString) return "Unknown Date";
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },

    formatStatusData(status: string): string {
      const statusMap: Record<string, string> = {
        add: "Added",
        update: "Updated",
        skip: "Skipped",
        failed: "Failed",
      };
      return statusMap[status] || status;
    },

    truncateTextData(text: string, maxLength: number): string {
      if (text.length <= maxLength) return text;
      return text.substring(0, maxLength) + "...";
    },

    // Table data transformation
    transformToTableDataData(items: ImportHistoryDetailItem[]) {
      return items.map((item: ImportHistoryDetailItem) => ({
        reference: item.reference,
        title: item.title,
        authors: item.authors,
        year: item.year,
        journal: item.journal || "N/A",
        status: item.status,
        associated_files: item.associated_files.join(", ") || "None",
        error_message: item.error_message || "None",
        actions: "actions",
      }));
    },
  };
}
