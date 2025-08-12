/**
 * Import analysis entities based on backend schemas
 * Maps to extralit-server/src/extralit_server/api/schemas/v1/imports.py
 */

// Basic field types supported in dataframes
export type FieldType = "string" | "integer" | "float" | "boolean";

// Import analysis status for individual documents (maps to ImportStatus enum in backend)
export type ImportStatus = "add" | "update" | "skip" | "ignore" | "failed";

// Document creation data for import (maps to DocumentCreate in backend)
// Only includes fields that are part of the backend DocumentCreate schema
// BibTeX fields (title, authors, year, journal, etc.) are stored in import_history.data
export interface DocumentCreate {
  workspace_id?: string;
  url?: string;
  file_name?: string;
  reference?: string;
  pmid?: string;
  doi?: string;
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

// Import history creation request (maps to ImportHistoryCreate in backend)
export interface ImportHistoryCreate {
  workspace_id: string;
  filename: string;
  data: Record<string, any>; // Tabular dataframe data converted from BibTeX file
  metadata?: Record<string, any>; // Import metadata including ImportStatus and associated files for each reference
}

// Import history response (maps to ImportHistoryResponse in backend)
export interface ImportHistoryResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  created_at: string;
  data?: DataframeData; // Tabular dataframe data (only in detailed view)
  metadata?: {
    documents: Record<string, DocumentImportAnalysis>; // Reference key to document info mapping
    summary: ImportSummary; // Import analysis summary
  };
}
