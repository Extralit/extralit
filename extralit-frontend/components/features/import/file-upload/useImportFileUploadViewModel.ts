/**
 * Shared view model for import file upload components
 * Provides common state management and strategy-based file type handling
 */

import { reactive, computed } from '@nuxtjs/composition-api';
import type { 
  FileUploadState, 
  FileUploadStrategy, 
  FileUploadViewModel,
  FileUploadPayload,
  BibStrategyOptions,
  PdfStrategyOptions
} from './types';
import type { CSVConfig } from '~/v1/domain/services/IFileParsingService';
import type { TableData } from '~/v1/domain/entities/table/TableData';

/**
 * Bibliography strategy for .bib and .csv files
 */
export function createBibStrategy(options: BibStrategyOptions): FileUploadStrategy {
  const { fileParsingService, onCsvConfigRequired, onCsvConfigComplete } = options;
  
  // Strategy-specific state
  const csvData = reactive({
    rawData: null,
    columns: [] as string[],
    previewRows: [] as any[],
    showColumnSelection: false,
    config: {
      referenceColumn: '',
      filesColumn: '',
    } as CSVConfig,
  });

  return {
    validateFiles(files: File[]): Promise<{ validFiles: File[]; errors: string[] }> {
      const validFiles: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!fileParsingService.isValidFileType(file, ['.bib', '.bibtex', '.csv'])) {
          errors.push(`${file.name}: Invalid file type. Expected .bib, .bibtex, or .csv`);
        } else if (file.size === 0) {
          errors.push(`${file.name}: File is empty`);
        } else if (file.size > 50 * 1024 * 1024) { // 50MB limit for text files
          errors.push(`${file.name}: File too large (max 50MB)`);
        } else {
          validFiles.push(file);
        }
      }

      return Promise.resolve({ validFiles, errors });
    },

    async processFiles(files: File[]): Promise<any> {
      if (files.length === 0) {
        throw new Error('No files to process');
      }

      const file = files[0]; // Only process first file for bibliography
      const content = await fileParsingService.readFileContent(file);
      
      const result = {
        fileName: file.name,
        rawContent: content,
        dataframeData: null as TableData | null,
        type: 'bibliography' as const,
      };

      if (this.isCsvFile(file)) {
        // Handle CSV with column selection
        const previewData = await fileParsingService.parseCSVForPreview(content);
        
        Object.assign(csvData, {
          rawData: previewData.rawData,
          columns: previewData.columns,
          previewRows: previewData.previewRows,
          showColumnSelection: true,
        });

        // Notify parent that CSV config is required
        if (onCsvConfigRequired) {
          onCsvConfigRequired(previewData);
        }

        // Return partial result - will be completed when CSV config is provided
        return { ...result, csvData };
      } else {
        // Handle BibTeX directly
        result.dataframeData = await fileParsingService.parseBibTeX(content);
        return result;
      }
    },

    isValid(data: any): boolean {
      return !!(data?.dataframeData?.data?.length > 0);
    },

    reset(): void {
      Object.assign(csvData, {
        rawData: null,
        columns: [],
        previewRows: [],
        showColumnSelection: false,
        config: {
          referenceColumn: '',
          filesColumn: '',
        },
      });
    },

    getConstants() {
      return {
        maxFileSize: 50 * 1024 * 1024, // 50MB
        acceptedExtensions: ['.bib', '.bibtex', '.csv'],
        supportedFormats: '.bib, .bibtex, .csv',
      };
    },

    // Strategy-specific methods
    isCsvFile(file: File): boolean {
      return file.name.toLowerCase().endsWith('.csv');
    },

    isBibTexFile(file: File): boolean {
      const fileName = file.name.toLowerCase();
      return fileName.endsWith('.bib') || fileName.endsWith('.bibtex');
    },

    async processCsvWithConfig(config: CSVConfig): Promise<any> {
      if (!config.referenceColumn) {
        throw new Error('Please select a reference column to continue.');
      }

      if (!csvData.rawData || csvData.rawData.length === 0) {
        throw new Error('No CSV data available. Please upload a file first.');
      }

      csvData.config = config;
      const dataframeData = await fileParsingService.parseCSVWithConfig(csvData.rawData, config);
      
      csvData.showColumnSelection = false;
      
      if (onCsvConfigComplete) {
        onCsvConfigComplete(config);
      }

      return dataframeData;
    },

    getCsvData() {
      return csvData;
    },
  } as FileUploadStrategy & {
    isCsvFile: (file: File) => boolean;
    isBibTexFile: (file: File) => boolean;
    processCsvWithConfig: (config: CSVConfig) => Promise<any>;
    getCsvData: () => typeof csvData;
  };
}

/**
 * PDF strategy for PDF file uploads and matching
 */
export function createPdfStrategy(options: PdfStrategyOptions): FileUploadStrategy {
  const { pdfMatchingService, maxFileSize = 200 * 1024 * 1024 } = options;
  let bibliographyEntries = options.bibliographyEntries;

  return {
    validateFiles(files: File[]): Promise<{ validFiles: File[]; errors: string[] }> {
      const validFiles: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!this.isValidPdfFile(file)) {
          errors.push(`${file.name}: Invalid file type. Expected PDF`);
        } else if (file.size === 0) {
          errors.push(`${file.name}: File is empty`);
        } else if (file.size > maxFileSize) {
          errors.push(`${file.name}: File too large (max ${Math.round(maxFileSize / 1024 / 1024)}MB)`);
        } else {
          validFiles.push(file);
        }
      }

      return Promise.resolve({ validFiles, errors });
    },

    processFiles(files: File[], existingData?: any): Promise<any> {
      // Get existing files to merge with new ones (support additive upload)
      const existingFiles = existingData ? [
        ...(existingData.matchedFiles?.map((mf: any) => mf.file) || []),
        ...(existingData.unmatchedFiles || [])
      ] : [];

      // Filter out duplicates by name
      const newFiles = files.filter(file => 
        !existingFiles.some((existing: File) => existing.name === file.name)
      );

      // Combine all files for matching
      const allFiles = [...existingFiles, ...newFiles];
      
      // Perform file matching
      const matchingResult = this.performFileMatching(allFiles);

      const result = {
        matchedFiles: matchingResult.matchedFiles,
        unmatchedFiles: matchingResult.unmatchedFiles,
        totalFiles: allFiles.length,
        type: 'pdf' as const,
      };

      return Promise.resolve(result);
    },

    isValid(data: any): boolean {
      return !!(data?.matchedFiles?.length > 0);
    },

    reset(): void {
      // PDF strategy doesn't maintain internal state
    },

    getConstants() {
      return {
        maxFileSize,
        acceptedExtensions: ['.pdf'],
        supportedFormats: '.pdf',
      };
    },

    // Strategy-specific methods
    isValidPdfFile(file: File): boolean {
      return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
    },

    performFileMatching(files: File[]): any {
      if (!bibliographyEntries?.data?.length || !files.length) {
        return {
          matchedFiles: [],
          unmatchedFiles: files,
        };
      }

      return pdfMatchingService.matchFiles(files, bibliographyEntries);
    },

    // Allow updating bibliography entries
    setBibliographyEntries(entries: any): void {
      bibliographyEntries = entries;
    },
  } as FileUploadStrategy & {
    isValidPdfFile: (file: File) => boolean;
    performFileMatching: (files: File[]) => any;
    setBibliographyEntries: (entries: any) => void;
  };
}

/**
 * Main composable factory for file upload view models
 */
export function useImportFileUploadViewModel(
  strategy: FileUploadStrategy,
  options: {
    onUpdate?: (payload: FileUploadPayload | null) => void;
    onError?: (error: string) => void;
  } = {}
): FileUploadViewModel {
  const { onUpdate, onError } = options;

  // Common state
  const state = reactive<FileUploadState & any>({
    isDragging: false,
    uploaded: false,
    hasError: false,
    errorMessage: '',
    processing: false,
    progress: 0,
    files: [],
    stats: {
      totalFiles: 0,
      processedFiles: 0,
    },
    // Allow strategy-specific state
    data: null,
  });

  // Computed properties
  const isValid = computed(() => {
    return state.data ? strategy.isValid(state.data) : false;
  });

  // Common drag/drop handling
  const dragEvents = {
    handleDragOver(event: DragEvent): void {
      event.preventDefault();
      state.isDragging = true;
    },

    handleDragLeave(): void {
      state.isDragging = false;
    },

    handleDrop(event: DragEvent): void {
      event.preventDefault();
      state.isDragging = false;

      const files = Array.from(event.dataTransfer?.files || []);
      selectFiles(files);
    },
  };

  // File selection and processing
  async function selectFiles(files: File[]): Promise<void> {
    if (files.length === 0) return;

    // Reset error state
    clearError();
    state.processing = true;
    state.progress = 0;

    try {
      // Validate files
      const { validFiles, errors } = await strategy.validateFiles(files);
      
      if (validFiles.length === 0) {
        throw new Error(errors.join('\n'));
      }

      if (errors.length > 0 && onError) {
        // Show partial errors but continue with valid files
        onError(`Some files could not be processed:\n${errors.join('\n')}`);
      }

      // Update stats
      state.stats.totalFiles = validFiles.length;
      state.stats.processedFiles = 0;

      // Process files with strategy
      const result = await strategy.processFiles(validFiles, state.data);
      
      // Update state
      state.data = result;
      state.files = validFiles;
      state.uploaded = true;
      state.processing = false;
      state.progress = 100;
      state.stats.processedFiles = validFiles.length;

      // Emit update
      if (onUpdate) {
        onUpdate(emitPayload());
      }

    } catch (error: any) {
      showError(error.message || 'Failed to process files');
    } finally {
      state.processing = false;
    }
  }

  function showError(message: string): void {
    state.hasError = true;
    state.errorMessage = message;
    state.uploaded = false;
    state.processing = false;
    
    if (onError) {
      onError(message);
    }
  }

  function clearError(): void {
    state.hasError = false;
    state.errorMessage = '';
  }

  function reset(): void {
    // Reset common state
    Object.assign(state, {
      isDragging: false,
      uploaded: false,
      hasError: false,
      errorMessage: '',
      processing: false,
      progress: 0,
      files: [],
      stats: {
        totalFiles: 0,
        processedFiles: 0,
      },
      data: null,
    });

    // Reset strategy-specific state
    strategy.reset();

    // Emit reset
    if (onUpdate) {
      onUpdate(null);
    }
  }

  function initialize(initialPayload?: any): void {
    if (initialPayload) {
      state.data = initialPayload;
      state.uploaded = strategy.isValid(initialPayload);
      state.hasError = false;
      state.errorMessage = '';
      state.processing = false;
    }
  }

  function emitPayload(): FileUploadPayload | null {
    return state.data && strategy.isValid(state.data) ? state.data : null;
  }

  return {
    state,
    selectFiles,
    reset,
    initialize,
    emitPayload,
    isValid: () => isValid.value,
    
    // Drag/drop helpers
    ...dragEvents,
    
    // Error handling helpers
    showError,
    clearError,
    
    // Strategy access for component-specific needs
    strategy,
  } as FileUploadViewModel & typeof dragEvents & {
    showError: (message: string) => void;
    clearError: () => void;
    strategy: FileUploadStrategy;
  };
}