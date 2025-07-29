/**
 * TypeScript type definitions for import-related data structures
 * Based on the backend schemas in argilla-server/src/argilla_server/api/schemas/v1/imports.py
 */

// Basic field types supported in dataframes
export type FieldType = 'string' | 'integer' | 'float' | 'boolean';

// Dataframe field definition
export interface DataframeField {
  name: string;
  type: FieldType;
}

// Dataframe schema definition
export interface DataframeSchema {
  fields: DataframeField[];
  primaryKey: string[];
}

// Tabular dataframe representation
export interface DataframeData {
  schema: DataframeSchema;
  data: Record<string, any>[];
}


// PDF file matching information
export interface PdfFileInfo {
  filename: string;
  path: string;
  size: number;
  matched: boolean;
  matchedReference?: string;
  confidence?: number;
}

// Import analysis status for individual documents (maps to ImportStatus enum in backend)
export type ImportStatus = 'add' | 'update' | 'skip' | 'ignore' | 'failed';

// Document creation data for import (maps to DocumentCreate in backend)
export interface DocumentCreate {
  title?: string;
  authors?: string[];
  year?: string;
  journal?: string;
  volume?: string;
  pages?: string;
  doi?: string;
  url?: string;
  abstract?: string;
  keywords?: string[];
  reference?: string;
  pmid?: string;
  file_name?: string;
  workspace_id?: string;
  metadata?: Record<string, any>;
}

// Analysis result for a single document (maps to DocumentImportAnalysis in backend)
export interface DocumentImportAnalysis {
  document_create: DocumentCreate;
  associated_files: string[]; // PDF filenames matched to this reference
  status: ImportStatus;
  validation_errors: string[];
}

// Summary statistics for import analysis (maps to ImportSummary in backend)
export interface ImportSummary {
  total_documents: number;
  add_count: number;
  update_count: number;
  skip_count: number;
  failed_count: number;
}

// Complete import analysis response (maps to ImportAnalysisResponse in backend)
export interface ImportAnalysisResponse {
  documents: Record<string, DocumentImportAnalysis>; // Reference to document info mapping
  summary: ImportSummary;
}

export interface PdfUploadData {
  matchedFiles: PdfFileInfo[];
  unmatchedFiles: PdfFileInfo[];
  totalFiles: number;
}

// Action to take for a document during import execution (maps to DocumentImportAction in backend)
export interface DocumentImportAction {
  action: ImportStatus;
  associated_files: string[];
}

// Confirmed documents for import (Step 3 output)
export interface ImportConfirmationData {
  confirmedDocuments: Record<string, DocumentImportAction>;
  totalConfirmed: number;
  documentActions: Record<string, ImportStatus>;
}

// Upload progress tracking (Step 4)
export interface ImportUploadData {
  confirmedDocuments: Record<string, DocumentImportAction>;
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

// Import history creation request (maps to ImportHistoryCreate in backend)
export interface ImportHistoryCreate {
  workspace_id: string;
  filename: string;
  data: DataframeData; // Generic tabular dataframe data converted from source format
}

// Props for ImportAnalysisTable component
export interface ImportAnalysisTableProps {
  analysisData: ImportAnalysisResponse;
  loading: boolean;
}

// Events emitted by ImportAnalysisTable
export interface ImportAnalysisTableEvents {
  update: ImportConfirmationData;
  retry: void;
}