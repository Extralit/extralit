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

// BibTeX entry data structure (parsed from bibliography files)
export interface BibTexEntry {
  reference: string;
  title?: string;
  authors?: string | string[];
  year?: string | number;
  journal?: string;
  volume?: string;
  pages?: string;
  doi?: string;
  url?: string;
  abstract?: string;
  keywords?: string | string[];
  [key: string]: any; // Allow additional fields
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

// Import analysis status for individual documents
export type ImportStatus = 'add' | 'update' | 'skip' | 'ignore' | 'failed';

// Document creation data for import
export interface DocumentCreateData {
  title: string;
  authors: string[];
  year: string;
  journal?: string;
  volume?: string;
  pages?: string;
  doi?: string;
  url?: string;
  abstract?: string;
  keywords?: string[];
  metadata?: Record<string, any>;
}

// Analysis result for a single document
export interface DocumentAnalysisResult {
  reference: string;
  document_create: DocumentCreateData;
  associated_files: string[];
  status: ImportStatus;
  validation_errors: string[];
  existing_document_id?: string;
  similarity_score?: number;
}

// Summary statistics for import analysis
export interface ImportAnalysisSummary {
  total_documents: number;
  add_count: number;
  update_count: number;
  skip_count: number;
  failed_count: number;
}

// Complete import analysis response
export interface ImportAnalysisData {
  documents: Record<string, DocumentAnalysisResult>;
  summary: ImportAnalysisSummary;
}

// File upload data from Step 1
export interface BibUploadData {
  fileName: string;
  parsedEntries: BibTexEntry[];
  dataframeData: DataframeData | null;
  rawContent: string;
}

export interface PdfUploadData {
  matchedFiles: PdfFileInfo[];
  unmatchedFiles: PdfFileInfo[];
  totalFiles: number;
}

// Confirmed documents for import (Step 3 output)
export interface ConfirmedDocument {
  action: ImportStatus;
  document_create: DocumentCreateData;
  associated_files: string[];
}

export interface ImportConfirmationData {
  confirmedDocuments: Record<string, ConfirmedDocument>;
  totalConfirmed: number;
  documentActions: Record<string, ImportStatus>;
}

// Upload progress tracking (Step 4)
export interface ImportUploadData {
  confirmedDocuments: Record<string, ConfirmedDocument>;
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

// Props for ImportAnalysisTable component
export interface ImportAnalysisTableProps {
  analysisData: ImportAnalysisData;
  loading: boolean;
}

// Events emitted by ImportAnalysisTable
export interface ImportAnalysisTableEvents {
  update: ImportConfirmationData;
  retry: void;
}