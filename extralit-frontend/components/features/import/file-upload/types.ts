/**
 * Shared types for file upload components
 */

import { TableData } from "~/v1/domain/entities/table/TableData";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";

// Base file upload state
export interface FileUploadState {
  isDragging: boolean;
  uploaded: boolean;
  hasError: boolean;
  errorMessage: string;
  processing: boolean;
  progress: number;
  processedFiles: number;
  totalFiles: number;
}

// Bibliography specific data
export interface BibliographyData {
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
}

// PDF specific data
export interface PdfData {
  matchedFiles: any[];
  unmatchedFiles: any[];
  totalFiles: number;
}

// CSV specific data
export interface CsvData {
  rawData: any;
  columns: string[];
  previewRows: any[];
}

// File upload payloads for events
export interface BibliographyPayload {
  isValid: boolean;
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
  type: "bibliography";
}

export interface PdfPayload {
  isValid: boolean;
  matchedFiles: any[];
  unmatchedFiles: any[];
  totalFiles: number;
  type: "pdf";
}

export type FileUploadPayload = BibliographyPayload | PdfPayload;

// Strategy configuration
export interface FileUploadStrategy {
  maxFileSize?: number;
  acceptedExtensions: string[];
  validateFile: (file: File) => { valid: boolean; error?: string };
  processFiles: (files: File[]) => Promise<void>;
  getDropzoneIcon: () => string;
  getDropzoneText: () => string;
}

// Props for strategies
export interface BibStrategyProps {
  fileParsingService: any;
  initialData?: BibliographyData;
  onUpdate?: (payload: BibliographyPayload) => void;
}

export interface PdfStrategyProps {
  pdfMatchingService: any;
  bibliographyEntries?: any;
  initialData?: PdfData;
  onUpdate?: (payload: PdfPayload) => void;
}

// CSV specific types
export interface CsvState {
  showCsvColumnSelection: boolean;
  csvData: CsvData;
  csvConfig: CSVConfig;
}
