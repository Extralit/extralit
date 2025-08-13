/**
 * Types for import file upload composables and components
 */

import type { TableData } from "~/v1/domain/entities/table/TableData";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";

// Common file upload state
export interface FileUploadState {
  isDragging: boolean;
  uploaded: boolean;
  hasError: boolean;
  errorMessage: string;
  processing: boolean;
  progress: number;
  files: File[];
  stats: {
    totalFiles: number;
    processedFiles: number;
  };
}

// Bibliography-specific data
export interface BibliographyData {
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
  type: 'bibliography';
}

// PDF-specific data
export interface PdfData {
  matchedFiles: any[];
  unmatchedFiles: any[];
  totalFiles: number;
  type: 'pdf';
}

// CSV-specific data for column selection
export interface CsvData {
  rawData: any;
  columns: string[];
  previewRows: any[];
  showColumnSelection: boolean;
  config: CSVConfig;
}

// Union type for all file upload payloads
export type FileUploadPayload = BibliographyData | PdfData;

// File upload strategy interface
export interface FileUploadStrategy {
  validateFiles(files: File[]): Promise<{ validFiles: File[]; errors: string[] }>;
  processFiles(files: File[], existingData?: any): Promise<any>;
  isValid(data: any): boolean;
  reset(): void;
  getConstants(): {
    maxFileSize?: number;
    acceptedExtensions: string[];
    supportedFormats: string;
  };
}

// Factory options for creating strategies
export interface BibStrategyOptions {
  fileParsingService: any;
  onCsvConfigRequired?: (csvData: any) => void;
  onCsvConfigComplete?: (config: CSVConfig) => void;
}

export interface PdfStrategyOptions {
  pdfMatchingService: any;
  bibliographyEntries?: TableData | null;
  maxFileSize?: number;
}

// View model interface
export interface FileUploadViewModel {
  state: FileUploadState & any; // Allow additional strategy-specific state
  selectFiles(files: File[]): Promise<void>;
  reset(): void;
  initialize(initialPayload?: any): void;
  emitPayload(): FileUploadPayload | null;
  isValid(): boolean;
}