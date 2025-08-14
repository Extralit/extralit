/**
 * PDF strategy for file upload (PDF folder handling and matching)
 */

import type {
  FileUploadStrategy,
  PdfData,
  PdfPayload,
  PdfStrategyProps,
} from "./types";
import { FILE_UPLOAD_CONSTANTS } from "./useImportFileUploadViewModel";

export const createPdfStrategy = (props: PdfStrategyProps): FileUploadStrategy & {
  // Additional methods specific to PDF
  hasValidData: (data: PdfData) => boolean;
  createPayload: () => PdfPayload;
  setUpdateProgressCallback: (callback: (processed: number, total: number) => void) => void;
} => {
  const { pdfMatchingService, bibliographyEntries, initialData } = props;

  // Current data
  const currentData: PdfData = initialData || {
    matchedFiles: [],
    unmatchedFiles: [],
    totalFiles: 0,
  };

  // Progress tracking
  let progressCallback: ((processed: number, total: number) => void) | null = null;

  const strategy: FileUploadStrategy = {
    maxFileSize: FILE_UPLOAD_CONSTANTS.MAX_PDF_SIZE,
    acceptedExtensions: FILE_UPLOAD_CONSTANTS.ACCEPTED_PDF_EXTENSIONS,

    validateFile: (file: File) => {
      if (!isValidPdfFile(file)) {
        return { valid: false, error: `${file.name} is not a valid PDF file` };
      }

      if (strategy.maxFileSize && file.size > strategy.maxFileSize) {
        return { valid: false, error: `File ${file.name} is too large (max 200MB)` };
      }

      if (file.size === 0) {
        return { valid: false, error: `File ${file.name} is empty` };
      }

      return { valid: true };
    },

    processFiles: (files: File[]) => {
      if (files.length === 0) return Promise.resolve();

      // Get existing files to merge with new ones (additive upload)
      const existingFiles = [
        ...currentData.matchedFiles.map(mf => mf.file),
        ...currentData.unmatchedFiles
      ];

      const pdfFiles = files.filter(file => isValidPdfFile(file));

      if (pdfFiles.length === 0) {
        return Promise.reject(new Error("No valid PDF files found. Please select a folder containing PDF files."));
      }

      const validFiles: File[] = [];
      const fileErrors: string[] = [];

      // Validate each file
      for (let i = 0; i < pdfFiles.length; i++) {
        const file = pdfFiles[i];
        
        // Skip files that are already uploaded (by name)
        const isDuplicate = existingFiles.some(existingFile => existingFile.name === file.name);
        if (!isDuplicate) {
          const validation = strategy.validateFile(file);
          if (validation.valid) {
            validFiles.push(file);
          } else {
            fileErrors.push(`${file.name}: ${validation.error}`);
          }
        }
        
        // Update progress
        if (progressCallback) {
          progressCallback(i + 1, pdfFiles.length);
        }
      }

      // Combine existing files with new valid files
      const allFiles = [...existingFiles, ...validFiles];
      currentData.totalFiles = allFiles.length;

      // Perform file matching with all files
      performFileMatching(allFiles);

      // Handle errors
      if (fileErrors.length > 0) {
        const successCount = validFiles.length;
        const errorCount = fileErrors.length;
        const totalCount = successCount + errorCount;

        let errorMessage = `Processed ${successCount} of ${totalCount} files successfully.\n\n`;
        errorMessage += `Files that could not be processed:\n${fileErrors.join('\n')}`;

        return Promise.reject(new Error(errorMessage));
      }

      return Promise.resolve();
    },

    getDropzoneIcon: () => "import",
    getDropzoneText: () => "Upload PDF Files",
  };

  // PDF specific methods
  const isValidPdfFile = (file: File): boolean => {
    return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  };

  const performFileMatching = (uploadedFiles: File[]) => {
    if (!bibliographyEntries || !bibliographyEntries.data || bibliographyEntries.data.length === 0 || uploadedFiles.length === 0) {
      // If no bibliography entries, all files are unmatched
      currentData.matchedFiles = [];
      currentData.unmatchedFiles = uploadedFiles;
      return;
    }

    const result = pdfMatchingService.matchFiles(uploadedFiles, bibliographyEntries);
    currentData.matchedFiles = result.matchedFiles;
    currentData.unmatchedFiles = result.unmatchedFiles;
  };

  const hasValidData = (data: PdfData): boolean => {
    return data && (data.matchedFiles.length > 0 || data.unmatchedFiles.length > 0 || data.totalFiles > 0);
  };

  const createPayload = (): PdfPayload => {
    return {
      isValid: currentData.matchedFiles.length > 0,
      matchedFiles: currentData.matchedFiles,
      unmatchedFiles: currentData.unmatchedFiles,
      totalFiles: currentData.totalFiles,
      type: 'pdf',
    };
  };

  const setProgressCallback = (callback: (processed: number, total: number) => void) => {
    progressCallback = callback;
  };

  return {
    ...strategy,
    hasValidData,
    createPayload,
    setUpdateProgressCallback: setProgressCallback,
  };
};