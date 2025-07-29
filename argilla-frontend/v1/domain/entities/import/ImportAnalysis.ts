/**
 * Import analysis entities based on backend schemas
 * Maps to argilla-server/src/argilla_server/api/schemas/v1/imports.py
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

// File information for import analysis
export interface FileInfo {
  filename: string;
  size: number;
}

// Document metadata for import analysis request
export interface DocumentMetadata {
  document_create: DocumentCreate;
  associated_files: FileInfo[];
}

// Import analysis request (maps to ImportAnalysisRequest in backend)
export interface ImportAnalysisRequest {
  workspace_id: string;
  documents: Record<string, DocumentMetadata>;
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

// Action to take for a document during import execution (maps to DocumentImportAction in backend)
export interface DocumentImportAction {
  action: ImportStatus;
  associated_files: string[];
}

// Import history creation request (maps to ImportHistoryCreate in backend)
export interface ImportHistoryCreate {
  workspace_id: string;
  filename: string;
  data: DataframeData; // Generic tabular dataframe data converted from source format
}