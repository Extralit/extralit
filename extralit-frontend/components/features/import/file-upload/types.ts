/**
 * Shared types for import file upload components
 */

import { TableData } from "~/v1/domain/entities/table/TableData";
import type { FileMatchResult } from "~/v1/domain/services/IFileMatchingService";

// Common file upload state interface
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

// Bibliography/CSV specific data
export interface BibliographyData {
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
  type: 'bibliography';
}

// PDF specific data
export interface PdfData {
  matchedFiles: FileMatchResult[];
  unmatchedFiles: File[];
  totalFiles: number;
  type: 'pdf';
}

// CSV specific data for column selection
export interface CsvData {
  rawData: any;
  columns: string[];
  previewRows: any[];
}

// Unified payload types for emitted events
export interface BibliographyPayload {
  isValid: boolean;
  fileName: string;
  dataframeData: TableData | null;
  rawContent: string;
  type: 'bibliography';
}

export interface PdfPayload {
  isValid: boolean;
  matchedFiles: FileMatchResult[];
  unmatchedFiles: File[];
  totalFiles: number;
  type: 'pdf';
}

export type FileUploadPayload = BibliographyPayload | PdfPayload;

// Strategy interface for different file upload types
export interface FileUploadStrategy<TData, TPayload extends FileUploadPayload> {
  // State management
  data: TData;
  
  // File validation and processing
  validateFiles(files: File[]): Promise<{ valid: File[], errors: string[] }>;
  processFiles(files: File[]): Promise<void>;
  
  // Initialization and reset
  initialize(initialData: TData): void;
  reset(): void;
  
  // Payload creation
  createPayload(): TPayload;
  isValid(): boolean;
}

// Configuration for file upload strategies
export interface FileUploadConfig {
  maxFileSize?: number;
  acceptedExtensions?: string[];
  enableDragDrop?: boolean;
  allowMultiple?: boolean;
}