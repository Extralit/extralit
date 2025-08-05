/**
 * View model for ImportHistoryDetails component
 * Handles loading and processing of import history details
 */

import { useResolve } from "ts-injecty";
import type { ImportHistoryResponse, DataframeData, ImportSummary } from "~/v1/domain/entities/import/ImportAnalysis";
import {
  GetImportHistoryDetailsUseCase,
  ImportHistoryDetailItem,
  ImportHistoryDetailsResponse,
} from "~/v1/domain/usecases/get-import-history-details-use-case";

// Legacy interface for backward compatibility
export interface ImportHistoryDetailsFilters {
  reference?: string;
  title?: string;
  authors?: string;
  status?: string;
  error_message?: string;
}

export function useImportHistoryDetailsViewModel(props: any) {
  const getImportHistoryDetailsUseCase = useResolve(GetImportHistoryDetailsUseCase);

  return {
    // Use case reference
    getImportHistoryDetailsUseCase,

    // Main data processing method
    processHistoryDetails(historyResponse: ImportHistoryResponse): {
      details: ImportHistoryDetailsResponse;
      items: ImportHistoryDetailItem[];
      summary: ImportSummary;
    } {
      // Ensure we have data for detailed view
      if (!historyResponse.data) {
        throw new Error("Import history data not available for detailed view");
      }

      const details: ImportHistoryDetailsResponse = {
        ...historyResponse,
        data: historyResponse.data,
        metadata: (historyResponse.metadata as ImportHistoryDetailsResponse["metadata"]) || {
          documents: {},
          summary: {
            total_documents: 0,
            add_count: 0,
            update_count: 0,
            skip_count: 0,
            failed_count: 0,
          },
        },
      };

      const items = this.processDetailItems(details);
      const summary = this.calculateSummary(historyResponse.data, historyResponse.metadata);

      return {
        details,
        items,
        summary,
      };
    },

    // Process dataframe data into detail items
    processDetailItems(details: ImportHistoryDetailsResponse): ImportHistoryDetailItem[] {
      return getImportHistoryDetailsUseCase.processDetailItems(details);
    },

    // Calculate summary from data and metadata
    calculateSummary(data: DataframeData, metadata?: ImportHistoryResponse["metadata"]): ImportSummary {
      return getImportHistoryDetailsUseCase.calculateSummary(data, metadata);
    },

    // Format authors for display
    formatAuthors(authors: string | string[] | undefined): string {
      if (!authors) return "Unknown Authors";
      if (Array.isArray(authors)) {
        return authors.slice(0, 3).join(", ") + (authors.length > 3 ? " et al." : "");
      }
      return String(authors);
    },

    // Legacy methods for backward compatibility with Vue components
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

    // Export helpers (legacy names for backward compatibility)
    createCSVContentData(items: ImportHistoryDetailItem[]): string {
      if (items.length === 0) {
        return "";
      }

      // Dynamically generate headers from the first item's fields
      const firstItem = items[0];
      const headers = Object.keys(firstItem).filter((key) => key !== "validation_errors" && key !== "associated_files");

      const rows = items.map((item) => {
        return headers.map((header) => {
          const value = item[header];
          if (header === "associated_files" && Array.isArray(value)) {
            return value.join("; ");
          }
          return String(value || "");
        });
      });

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

    // Formatting helpers (legacy names for backward compatibility)
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

    // Table data transformation (legacy name for backward compatibility)
    transformToTableDataData(items: ImportHistoryDetailItem[]) {
      return items.map((item: ImportHistoryDetailItem) => {
        const transformed: Record<string, any> = {
          reference: item.reference,
          status: item.status,
          associated_files: item.associated_files.join(", ") || "None",
          error_message: item.error_message || "None",
          actions: "actions",
        };

        // Add all other dynamic fields from the original data
        Object.entries(item).forEach(([key, value]) => {
          if (
            !["reference", "status", "associated_files", "error_message", "validation_errors", "actions"].includes(key)
          ) {
            transformed[key] = value || "N/A";
          }
        });

        return transformed;
      });
    },

    // New simplified methods (preferred going forward)
    createCSVContent(items: ImportHistoryDetailItem[]): string {
      return this.createCSVContentData(items);
    },

    downloadCSV(csvContent: string, filename: string): void {
      this.downloadCSVData(csvContent, filename);
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

    transformToTableData(items: ImportHistoryDetailItem[]) {
      return this.transformToTableDataData(items);
    },
  };
}
