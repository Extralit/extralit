/**
 * Frontend component types for import functionality
 * Backend API types are imported from ~/v1/domain/entities/import/ImportAnalysis.ts
 */

import type {
  ImportStatus,
  DocumentMetadata,
  DataframeData,
} from "~/v1/domain/entities/import/ImportAnalysis";

// Re-export commonly used backend types for convenience
export type {
  FieldType,
  DataframeField,
  DataframeSchema,
  DataframeData,
  ImportStatus,
  DocumentCreate,
  FileInfo,
  DocumentMetadata,
  ImportAnalysisRequest,
  DocumentImportAnalysis,
  ImportSummary,
  ImportAnalysisResponse,
  ImportHistoryCreate,
  ImportHistoryResponse,
} from "~/v1/domain/entities/import/ImportAnalysis";
export type { CellComponent } from "tabulator-tables";

export interface PdfFileInfo {
  filename: string;
  path: string;
  size: number;
  matched: boolean;
  matchedReference?: string;
  confidence?: number;
}

// PDF upload data
export interface PdfUploadData {
  matchedFiles: PdfFileInfo[];
  unmatchedFiles: PdfFileInfo[];
  totalFiles: number;
}

// Upload progress tracking (Step 4)
export interface ImportUploadData {
  confirmedDocuments: Record<string, DocumentMetadata>;
  totalBatches: number;
  currentBatch: number;
  jobIds: Record<string, string>;
  completedJobs: number;
  failedJobs: number;
}

// Final import summary (Step 5)
export interface ImportSummaryData {
  totalProcessed: number;
  successfullyAdded: number;
  updated: number;
  skipped: number;
  failed: number;
  errors: string[];
  importId: string | null;
}

// Import confirmation data (Step 3)
export interface ImportConfirmationData {
  confirmedDocuments: Record<string, DocumentMetadata>;
  totalConfirmed: number;
  documentActions: Record<string, ImportStatus>;
  filteredDataframeData: DataframeData | null;
}

// Table row data for ImportAnalysisTable
export interface AnalysisTableRow {
  reference: string;
  title: string;
  authors: string;
  year: string;
  files: string;
  filePaths: string[]; // Array of file paths for this reference
  status: ImportStatus;
  originalStatus: ImportStatus;
  validationErrors: string[];
  canToggle: boolean;
  // Dynamic fields from dataframe
  [key: string]: any;
}

// Column configuration for BaseSimpleTable
export interface TableColumn {
  field: string;
  title: string;
  width?: number;
  minWidth?: number;
  maxWidth?: number;
  frozen?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  headerFilter?: string;
  headerFilterParams?: Record<string, any>;
  formatter?: (cell: any) => string;
  cellClick?: (e: Event, cell: any) => void;
  cellDblClick?: (e: Event, cell: any) => void;
  cssClass?: string;
  resizable?: boolean;
  visible?: boolean;
  editor?: any;
  editorParams?: Record<string, any>;
  validator?: any;
}
