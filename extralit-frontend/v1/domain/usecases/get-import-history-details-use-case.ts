/**
 * Use case for fetching detailed import history data
 */

import type { AxiosInstance } from "axios";
import { TableData } from "../entities/table/TableData";
import type {
  ImportHistoryResponse,
  DocumentImportAnalysis,
  ImportStatus,
  ImportSummary,
} from "~/v1/domain/entities/import/ImportAnalysis";

export interface ImportHistoryDetailItem {
  reference: string;
  status: ImportStatus;
  associated_files: string[];
  error_message?: string;
  validation_errors?: string[];
  // Dynamic fields from original dataframe (title, authors, year, journal, etc.)
  [key: string]: any;
}

export interface ImportHistoryDetailsResponse extends ImportHistoryResponse {
  data: TableData;
  metadata: {
    documents: Record<string, DocumentImportAnalysis>; // Reference key to document info mapping
    summary: ImportSummary; // Import analysis summary
  };
}

export class GetImportHistoryDetailsUseCase {
  constructor(private readonly axios: AxiosInstance) {}

  async execute(importId: string): Promise<ImportHistoryDetailsResponse> {
    const response = await this.axios.get<ImportHistoryDetailsResponse>(`/v1/imports/history/${importId}`);

    return response.data;
  }

  /**
   * Process the import history response into detail items
   */
  processDetailItems(details: ImportHistoryDetailsResponse): ImportHistoryDetailItem[] {
    const items: ImportHistoryDetailItem[] = [];

    // Process each data row from the dataframe
    details.data.data.forEach((row: Record<string, any>) => {
      const reference = row.reference || row.id || "Unknown";
      const documentAnalysis: DocumentImportAnalysis = details.metadata?.documents?.[reference] || {
        document_create: {},
        associated_files: [],
        status: "unknown" as ImportStatus,
        validation_errors: [],
      };

      const item: ImportHistoryDetailItem = {
        reference,
        status: documentAnalysis.status,
        associated_files: documentAnalysis.associated_files,
        error_message: documentAnalysis.validation_errors?.join("; ") || undefined,
        validation_errors: documentAnalysis.validation_errors,
        // Include all fields from the original data with proper formatting
        ...this.formatDataFields(row),
      };

      items.push(item);
    });

    return items;
  }

  /**
   * Calculate summary from data and metadata
   */
  calculateSummary(data: TableData, metadata?: ImportHistoryResponse["metadata"]): ImportSummary {
    // If metadata already contains a summary, use it
    if (metadata?.summary) {
      return metadata.summary;
    }

    // Otherwise calculate from documents
    const summary = {
      total_documents: data.data.length,
      add_count: 0,
      update_count: 0,
      skip_count: 0,
      failed_count: 0,
    };

    if (metadata?.documents) {
      Object.values(metadata.documents).forEach((documentAnalysis: DocumentImportAnalysis) => {
        switch (documentAnalysis.status) {
          case "add":
            summary.add_count++;
            break;
          case "update":
            summary.update_count++;
            break;
          case "skip":
            summary.skip_count++;
            break;
          case "failed":
            summary.failed_count++;
            break;
          case "ignore":
            // Ignore status doesn't count towards any category
            break;
        }
      });
    }

    return summary;
  }

  private formatAuthors(authors: string | string[] | undefined): string {
    if (!authors) return "Unknown Authors";
    if (Array.isArray(authors)) {
      return authors.slice(0, 3).join(", ") + (authors.length > 3 ? " et al." : "");
    }
    return String(authors);
  }

  /**
   * Format data fields from the original dataframe
   */
  private formatDataFields(row: Record<string, any>): Record<string, any> {
    const formatted: Record<string, any> = {};

    // Process each field from the original data
    Object.entries(row).forEach(([key, value]) => {
      if (key === "reference" || key === "id") {
        // Skip reference/id as it's handled separately
        return;
      }

      // Format specific field types
      if (key === "authors" || key === "author") {
        formatted[key] = this.formatAuthors(value);
      } else if (key === "year") {
        formatted[key] = value?.toString() || "Unknown";
      } else if (key === "journal" || key === "venue") {
        formatted[key] = value || "Unknown";
      } else if (key === "title") {
        formatted[key] = value || "Unknown Title";
      } else {
        // For all other fields, use the original value
        formatted[key] = value;
      }
    });

    return formatted;
  }
}
