/**
 * View model for import file upload components
 * Provides shared state management and strategy-based file processing
 */

import { ref, computed } from "@nuxtjs/composition-api";
import type {
  FileUploadState,
  BibliographyData,
  PdfData,
  CsvData,
  BibliographyPayload,
  PdfPayload,
  FileUploadConfig,
  FileUploadPayload
} from "./types";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";
import { PdfMatchingService } from "~/v1/domain/services/FileMatchingService";
import { TableData } from "~/v1/domain/entities/table/TableData";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";

// Constants
const DEFAULT_MAX_PDF_SIZE = 200 * 1024 * 1024; // 200MB
const ACCEPTED_BIB_EXTENSIONS = [".bib", ".bibtex", ".csv"];

/**
 * Bibliography/CSV upload strategy implementation
 */
export function createBibStrategy(fileParsingService: FileParsingService) {
  const data = ref<BibliographyData>({
    fileName: "",
    dataframeData: null,
    rawContent: "",
    type: 'bibliography'
  });

  // CSV-specific state for column selection
  const csvData = ref<CsvData>({
    rawData: null,
    columns: [],
    previewRows: [],
  });
  const csvConfig = ref<CSVConfig>({
    referenceColumn: "",
    filesColumn: "",
  });
  const showCsvColumnSelection = ref(false);

  const strategy = {
    data,

    async validateFiles(files: File[]) {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!fileParsingService.isValidFileType(file, ACCEPTED_BIB_EXTENSIONS)) {
          errors.push(`${file.name}: Invalid file type. Please upload a .bib, .bibtex, or .csv file.`);
        } else {
          valid.push(file);
        }
      }

      return { valid, errors };
    },

    async processFiles(files: File[]) {
      if (files.length === 0) return;
      
      const file = files[0]; // Only process first file for bibliography
      data.value.fileName = file.name;

      try {
        // Read file content
        const content = await fileParsingService.readFileContent(file);
        data.value.rawContent = content;

        if (strategy.isCsvFile(file)) {
          // Handle CSV file - set up for column selection
          const previewData = await fileParsingService.parseCSVForPreview(content);
          csvData.value = {
            rawData: previewData.rawData,
            columns: previewData.columns,
            previewRows: previewData.previewRows,
          };
          showCsvColumnSelection.value = true;
        } else if (strategy.isBibTexFile(file)) {
          // Handle BibTeX file - process directly
          data.value.dataframeData = await fileParsingService.parseBibTeX(content);
          if (!data.value.dataframeData || data.value.dataframeData.data.length === 0) {
            throw new Error("No valid BibTeX entries found in the file.");
          }
        }
      } catch (error: any) {
        throw new Error(`Failed to process file: ${error.message}`);
      }
    },

    initialize(initialData: BibliographyData) {
      data.value = {
        fileName: initialData.fileName || "",
        dataframeData: initialData.dataframeData || null,
        rawContent: initialData.rawContent || "",
        type: 'bibliography'
      };
      
      // Reset CSV state when initializing
      showCsvColumnSelection.value = false;
      csvData.value = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      csvConfig.value = {
        referenceColumn: "",
        filesColumn: "",
      };
    },

    reset() {
      data.value = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
        type: 'bibliography'
      };
      showCsvColumnSelection.value = false;
      csvData.value = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      csvConfig.value = {
        referenceColumn: "",
        filesColumn: "",
      };
    },

    createPayload(): BibliographyPayload {
      return {
        isValid: strategy.isValid(),
        fileName: data.value.fileName,
        dataframeData: data.value.dataframeData,
        rawContent: data.value.rawContent,
        type: 'bibliography'
      };
    },

    isValid() {
      return data.value.dataframeData && data.value.dataframeData.data.length > 0;
    },

    // CSV-specific methods
    isCsvFile(file: File) {
      return file.name.toLowerCase().endsWith(".csv");
    },

    isBibTexFile(file: File) {
      const fileName = file.name.toLowerCase();
      return fileName.endsWith(".bib") || fileName.endsWith(".bibtex");
    },

    // CSV processing methods
    async processCsvWithConfig() {
      if (!csvConfig.value.referenceColumn) {
        throw new Error("Please select a reference column to continue.");
      }

      if (!csvData.value.rawData || csvData.value.rawData.length === 0) {
        throw new Error("No CSV data available. Please upload a file first.");
      }

      data.value.dataframeData = await fileParsingService.parseCSVWithConfig(
        csvData.value.rawData, 
        csvConfig.value
      );
      showCsvColumnSelection.value = false;
    },

    handleCsvConfigUpdate(config: CSVConfig) {
      csvConfig.value = config;
    },

    cancelCsvSelection() {
      showCsvColumnSelection.value = false;
      strategy.reset();
    },

    // Expose CSV state for components
    csvData,
    csvConfig,
    showCsvColumnSelection,
  };

  return strategy;
}

/**
 * PDF upload strategy implementation
 */
export function createPdfStrategy(
  pdfMatchingService: PdfMatchingService,
  config: FileUploadConfig = {}
) {
  const maxSize = config.maxFileSize || DEFAULT_MAX_PDF_SIZE;
  
  const data = ref<PdfData>({
    matchedFiles: [],
    unmatchedFiles: [],
    totalFiles: 0,
    type: 'pdf'
  });

  const strategy = {
    data,

    async validateFiles(files: File[]) {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!strategy.isValidPdfFile(file)) {
          errors.push(`${file.name}: Invalid file type. Only PDF files are supported.`);
        } else if (file.size > maxSize) {
          errors.push(`${file.name}: File too large (max ${Math.round(maxSize / 1024 / 1024)}MB)`);
        } else if (file.size === 0) {
          errors.push(`${file.name}: File is empty`);
        } else {
          valid.push(file);
        }
      }

      return { valid, errors };
    },

    async processFiles(files: File[]) {
      // Get existing files to merge with new ones (for additive upload)
      const existingFiles = [
        ...data.value.matchedFiles.map(mf => mf.file),
        ...data.value.unmatchedFiles
      ];

      // Filter out duplicates by name
      const newFiles = files.filter(file => 
        !existingFiles.some(existingFile => existingFile.name === file.name)
      );

      // Combine all files
      const allFiles = [...existingFiles, ...newFiles];
      data.value.totalFiles = allFiles.length;

      // No additional processing needed for PDFs - matching happens separately
    },

    performFileMatching(uploadedFiles: File[], bibliographyEntries: TableData | null) {
      if (!bibliographyEntries || !bibliographyEntries.data || bibliographyEntries.data.length === 0) {
        // If no bibliography entries, all files are unmatched
        data.value.matchedFiles = [];
        data.value.unmatchedFiles = uploadedFiles;
        return;
      }

      const result = pdfMatchingService.matchFiles(uploadedFiles, bibliographyEntries);
      data.value.matchedFiles = result.matchedFiles;
      data.value.unmatchedFiles = result.unmatchedFiles;
    },

    initialize(initialData: PdfData) {
      data.value = {
        matchedFiles: initialData.matchedFiles || [],
        unmatchedFiles: initialData.unmatchedFiles || [],
        totalFiles: initialData.totalFiles || 0,
        type: 'pdf'
      };
    },

    reset() {
      data.value = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
        type: 'pdf'
      };
    },

    createPayload(): PdfPayload {
      return {
        isValid: strategy.isValid(),
        matchedFiles: data.value.matchedFiles,
        unmatchedFiles: data.value.unmatchedFiles,
        totalFiles: data.value.totalFiles,
        type: 'pdf'
      };
    },

    isValid() {
      return data.value.matchedFiles.length > 0;
    },

    isValidPdfFile(file: File) {
      return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    },
  };

  return strategy;
}

/**
 * Main composable factory for file upload functionality
 */
export function useImportFileUploadViewModel(
  strategy: any,
  config: FileUploadConfig = {}
) {
  // Common state
  const state = ref<FileUploadState>({
    isDragging: false,
    uploaded: false,
    hasError: false,
    errorMessage: "",
    processing: false,
    progress: 0,
    processedFiles: 0,
    totalFiles: 0,
  });

  // Computed properties
  const isValid = computed(() => strategy.isValid());
  
  const progressPercentage = computed(() => {
    if (state.value.totalFiles === 0) return 0;
    return Math.round((state.value.processedFiles / state.value.totalFiles) * 100);
  });

  // Common methods
  const selectFiles = async (files: File[]) => {
    try {
      state.value.hasError = false;
      state.value.errorMessage = "";
      state.value.processing = true;
      state.value.processedFiles = 0;

      // Validate files
      const { valid, errors } = await strategy.validateFiles(files);
      
      if (valid.length === 0 && errors.length > 0) {
        throw new Error(errors.join('\n'));
      }

      state.value.totalFiles = valid.length;

      // Process files
      await strategy.processFiles(valid);
      
      state.value.uploaded = true;
      state.value.processedFiles = valid.length;

      // Show partial errors if any
      if (errors.length > 0) {
        const successCount = valid.length;
        const errorCount = errors.length;
        const totalCount = successCount + errorCount;
        
        let errorMessage = `Processed ${successCount} of ${totalCount} files successfully.\n\n`;
        errorMessage += `Files that could not be processed:\n${errors.join('\n')}`;
        showError(errorMessage);
      }

    } catch (error: any) {
      showError(error.message);
    } finally {
      state.value.processing = false;
    }
  };

  const reset = () => {
    // Reset common state
    state.value = {
      isDragging: false,
      uploaded: false,
      hasError: false,
      errorMessage: "",
      processing: false,
      progress: 0,
      processedFiles: 0,
      totalFiles: 0,
    };
    
    // Reset strategy-specific state
    strategy.reset();
  };

  const initialize = (initialData: any) => {
    strategy.initialize(initialData);
    
    // Update common state based on initialized data
    state.value.uploaded = strategy.isValid();
    state.value.hasError = false;
    state.value.errorMessage = "";
    state.value.processing = false;
  };

  const emitPayload = () => strategy.createPayload();

  // Drag and drop handlers
  const handleDragOver = (event: DragEvent) => {
    if (config.enableDragDrop === false) return;
    event.preventDefault();
    state.value.isDragging = true;
  };

  const handleDragLeave = () => {
    if (config.enableDragDrop === false) return;
    state.value.isDragging = false;
  };

  const handleDrop = async (event: DragEvent) => {
    if (config.enableDragDrop === false) return;
    event.preventDefault();
    state.value.isDragging = false;

    const files = Array.from(event.dataTransfer?.files || []);
    await selectFiles(files);
  };

  // Error handling
  const showError = (message: string) => {
    state.value.hasError = true;
    state.value.errorMessage = message;
    state.value.uploaded = false;
  };

  const clearError = () => {
    state.value.hasError = false;
    state.value.errorMessage = "";
  };

  // UI helpers
  const getDropzoneIcon = computed(() => {
    if (state.value.hasError) return "danger";
    if (state.value.uploaded) return "check";
    return strategy.data.value.type === 'pdf' ? "import" : "document";
  });

  const getDropzoneText = computed(() => {
    if (state.value.hasError) return `Error processing ${strategy.data.value.type} files`;
    if (state.value.uploaded) return `Upload ${strategy.data.value.type === 'pdf' ? 'PDF' : 'BibTeX'} Files`;
    return `Upload ${strategy.data.value.type === 'pdf' ? 'PDF' : 'BibTeX'} Files`;
  });

  return {
    // State
    state,
    
    // Computed
    isValid,
    progressPercentage,
    
    // Methods
    selectFiles,
    reset,
    initialize,
    emitPayload,
    
    // Drag and drop
    handleDragOver,
    handleDragLeave,
    handleDrop,
    
    // Error handling
    showError,
    clearError,
    
    // UI helpers
    getDropzoneIcon,
    getDropzoneText,
    
    // Strategy access
    strategy,
  };
}