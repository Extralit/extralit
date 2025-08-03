/**
 * ImportHistory Details entity types
 * Provides TypeScript interfaces for ImportHistory data structure
 */

import { ImportHistoryDetailsResponse } from "../../usecases/get-import-history-details-use-case";

// Re-export the interfaces from the use case for consistency
export {
  ImportHistoryDetailItem,
  ImportHistoryDetailsResponse,
  ImportHistoryDetailsFilters,
  ImportHistoryDetailsParams,
} from "../../usecases/get-import-history-details-use-case";

// Additional entity types specific to ImportHistory details
export interface ImportHistoryDataField {
  name: string;
  type: "string" | "integer" | "float" | "boolean";
  nullable?: boolean;
  description?: string;
}

export interface ImportHistoryDataSchema {
  fields: ImportHistoryDataField[];
  primaryKey: string[];
  totalRows: number;
}

export interface ImportHistoryMetadata {
  [reference: string]: {
    status: "add" | "update" | "skip" | "failed";
    associated_files: string[];
    error_message?: string;
    validation_errors?: string[];
    import_timestamp?: string;
  };
}

export interface ImportHistorySummaryStats {
  total_documents: number;
  add_count: number;
  update_count: number;
  skip_count: number;
  failed_count: number;
  success_rate: number;
}

/**
 * Enhanced ImportHistory details with computed properties
 */
export class ImportHistoryDetails {
  constructor(private readonly data: ImportHistoryDetailsResponse) {}

  get id(): string {
    return this.data.id;
  }

  get workspaceId(): string {
    return this.data.workspace_id;
  }

  get filename(): string {
    return this.data.filename;
  }

  get createdAt(): Date {
    return new Date(this.data.created_at);
  }

  get uploadedBy(): string | undefined {
    return this.data.uploaded_by;
  }

  get schema(): ImportHistoryDataSchema {
    return {
      fields: this.data.data.schema.fields.map((field) => ({
        name: field.name,
        type: field.type as "string" | "integer" | "float" | "boolean",
      })),
      primaryKey: this.data.data.schema.primaryKey,
      totalRows: this.data.data.data.length,
    };
  }

  get records(): Record<string, any>[] {
    return this.data.data.data;
  }

  get metadata(): ImportHistoryMetadata {
    return this.data.metadata || {};
  }

  get summary(): ImportHistorySummaryStats {
    return {
      ...this.data.summary,
      success_rate:
        this.data.summary.total_documents > 0
          ? (this.data.summary.add_count + this.data.summary.update_count) / this.data.summary.total_documents
          : 0,
    };
  }

  get fieldNames(): string[] {
    return this.schema.fields.map((field) => field.name);
  }

  get hasErrors(): boolean {
    return this.summary.failed_count > 0;
  }

  get isSuccessful(): boolean {
    return this.summary.success_rate > 0.8; // Consider successful if >80% success rate
  }

  /**
   * Get a sample record for field mapping preview
   */
  getSampleRecord(): Record<string, any> {
    return this.records.length > 0 ? this.records[0] : {};
  }

  /**
   * Get records by status
   */
  getRecordsByStatus(status: "add" | "update" | "skip" | "failed"): Record<string, any>[] {
    return this.records.filter((record) => {
      const reference = record.reference || record.id;
      const recordMetadata = this.metadata[reference];
      return recordMetadata?.status === status;
    });
  }

  /**
   * Get field statistics for data preview
   */
  getFieldStats(fieldName: string): {
    totalValues: number;
    uniqueValues: number;
    nullValues: number;
    sampleValues: any[];
  } {
    const values = this.records.map((record) => record[fieldName]);
    const nonNullValues = values.filter((value) => value != null);
    const uniqueValues = new Set(nonNullValues);

    return {
      totalValues: values.length,
      uniqueValues: uniqueValues.size,
      nullValues: values.length - nonNullValues.length,
      sampleValues: Array.from(uniqueValues).slice(0, 5), // First 5 unique values
    };
  }

  /**
   * Check if a field contains text suitable for annotation
   */
  isTextAnnotationField(fieldName: string): boolean {
    const field = this.schema.fields.find((f) => f.name === fieldName);
    if (!field || field.type !== "string") return false;

    const stats = this.getFieldStats(fieldName);
    const avgLength =
      stats.sampleValues.filter((value) => typeof value === "string").reduce((sum, value) => sum + value.length, 0) /
      stats.sampleValues.length;

    // Consider it a text field if average length > 50 characters
    return avgLength > 50;
  }

  /**
   * Get raw data for export or further processing
   */
  getRawData(): ImportHistoryDetailsResponse {
    return this.data;
  }
}
