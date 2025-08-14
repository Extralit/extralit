/**
 * Bibliography strategy for file upload (BibTeX/CSV handling)
 */

import { FILE_UPLOAD_CONSTANTS } from "./useImportFileUploadViewModel";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";
import type {
  FileUploadStrategy,
  BibliographyData,
  BibliographyPayload,
  BibStrategyProps,
  CsvState,
} from "./types";

export const createBibStrategy = (props: BibStrategyProps) => {
  const { fileParsingService, initialData, onUpdate } = props;

  // CSV-specific state (reactive externally)
  const csvState: CsvState = {
    showCsvColumnSelection: false,
    csvData: {
      rawData: null,
      columns: [],
      previewRows: [],
    },
    csvConfig: {
      referenceColumn: "",
      filesColumn: "",
    },
  };

  // Current data (managed separately from the composable)
  let currentData: BibliographyData = initialData || {
    fileName: "",
    dataframeData: null,
    rawContent: "",
  };

  const strategy: FileUploadStrategy = {
    acceptedExtensions: FILE_UPLOAD_CONSTANTS.ACCEPTED_BIB_EXTENSIONS,

    validateFile: (file: File) => {
      if (!fileParsingService.isValidFileType(file, strategy.acceptedExtensions)) {
        return { valid: false, error: "Invalid file type. Please upload a .bib, .bibtex, or .csv file." };
      }
      return { valid: true };
    },

    processFiles: async (files: File[]) => {
      if (files.length === 0) return;
      
      const file = files[0]; // Bibliography only handles single file
      
      // Reset state
      currentData = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };

      // Reset CSV state
      csvState.showCsvColumnSelection = false;
      csvState.csvData = {
        rawData: null,
        columns: [],
        previewRows: [],
      };
      csvState.csvConfig = {
        referenceColumn: "",
        filesColumn: "",
      };

      // Validate file
      const validation = strategy.validateFile(file);
      if (!validation.valid) {
        throw new Error(validation.error!);
      }

      currentData.fileName = file.name;

      // Read file content
      const content = await fileParsingService.readFileContent(file);
      currentData.rawContent = content;

      if (isCsvFile(file)) {
        // Handle CSV file - show column selection
        await parseCsvContent(content);
      } else if (isBibTexFile(file)) {
        // Handle BibTeX file - direct processing
        currentData.dataframeData = await fileParsingService.parseBibTeX(content);

        if (!currentData.dataframeData || currentData.dataframeData.data.length === 0) {
          throw new Error("No valid BibTeX entries found in the file.");
        }
      }
    },

    getDropzoneIcon: () => "document",
    getDropzoneText: () => "Upload BibTeX File",
  };

  // CSV specific methods
  const parseCsvContent = async (content: string) => {
    try {
      const previewData = await fileParsingService.parseCSVForPreview(content);

      csvState.csvData = {
        rawData: previewData.rawData,
        columns: previewData.columns,
        previewRows: previewData.previewRows,
      };

      csvState.showCsvColumnSelection = true;
    } catch (error: any) {
      throw new Error(`CSV parsing failed: ${error.message}`);
    }
  };

  const processCsvWithConfig = async () => {
    try {
      if (!csvState.csvConfig.referenceColumn) {
        throw new Error("Please select a reference column to continue.");
      }

      if (!csvState.csvData.rawData || csvState.csvData.rawData.length === 0) {
        throw new Error("No CSV data available. Please upload a file first.");
      }

      currentData.dataframeData = await fileParsingService.parseCSVWithConfig(
        csvState.csvData.rawData, 
        csvState.csvConfig
      );

      csvState.showCsvColumnSelection = false;

      if (onUpdate) {
        onUpdate(createPayload());
      }
    } catch (error: any) {
      throw new Error(`Failed to process CSV data: ${error.message}`);
    }
  };

  const handleCsvConfigUpdate = (config: CSVConfig) => {
    csvState.csvConfig = config;
  };

  const cancelCsvSelection = () => {
    csvState.showCsvColumnSelection = false;
    csvState.csvData = {
      rawData: null,
      columns: [],
      previewRows: [],
    };
    csvState.csvConfig = {
      referenceColumn: "",
      filesColumn: "",
    };

    currentData = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
    };
  };

  const isCsvFile = (file: File): boolean => {
    return file.name.toLowerCase().endsWith(".csv");
  };

  const isBibTexFile = (file: File): boolean => {
    const fileName = file.name.toLowerCase();
    return fileName.endsWith(".bib") || fileName.endsWith(".bibtex");
  };

  const hasValidData = (data: BibliographyData): boolean => {
    return Boolean(data && (data.fileName || (data.dataframeData && data.dataframeData.data.length > 0)));
  };

  const createPayload = (): BibliographyPayload => {
    return {
      isValid: !!(currentData.dataframeData && currentData.dataframeData.data.length > 0),
      fileName: currentData.fileName,
      dataframeData: currentData.dataframeData,
      rawContent: currentData.rawContent,
      type: 'bibliography',
    };
  };

  return {
    ...strategy,
    csvState,
    processCsvWithConfig,
    handleCsvConfigUpdate,
    cancelCsvSelection,
    isCsvFile,
    isBibTexFile,
    hasValidData,
    createPayload,
  };
};