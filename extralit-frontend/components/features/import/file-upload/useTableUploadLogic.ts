/**
 * Helper composable for TableUpload component
 * Gradual migration to Composition API while maintaining existing structure
 */

import { ref, watch, onMounted, computed } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import type { BibliographyData, CsvData } from "./types";
import type { CSVConfig } from "~/v1/domain/services/IFileParsingService";
import { FileParsingService } from "~/v1/domain/services/FileParsingService";

export const useTableUploadLogic = (
  props: { initialData: BibliographyData },
  emit?: (event: string, data: any) => void
) => {
  const fileService = useResolve(FileParsingService);

  // Reactive state
  const dragOver = ref(false);
  const uploaded = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");
  const fileInput = ref<HTMLInputElement | null>(null);

  const data = ref<BibliographyData>({
    fileName: "",
    dataframeData: null,
    rawContent: "",
  });

  // CSV parsing state
  const showCsvColumnSelection = ref(false);
  const csvData = ref<CsvData>({
    rawData: null,
    columns: [],
    previewRows: [],
  });
  const csvConfig = ref<CSVConfig>({
    referenceColumn: "",
    filesColumn: "",
  });

  // Computed properties
  const getDropzoneIcon = computed(() => {
    if (hasError.value) return "danger";
    if (uploaded.value) return "check";
    return "import";
  });

  const getDropzoneText = computed(() => {
    if (hasError.value) return "Error parsing bibliography file";
    if (uploaded.value) return "Drop file here";
    return "Drop file here";
  });

  // Drag and drop handlers
  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    dragOver.value = true;
  };

  const handleDragLeave = () => {
    dragOver.value = false;
  };

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    dragOver.value = false;

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  // File input handling
  const triggerFileInput = () => {
    fileInput.value?.click();
  };

  const handleFileSelect = (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = target.files;
    if (files && files.length > 0) {
      processFile(files[0]);
    }
  };

  // Watch for changes and emit updates
  const emitUpdate = () => {
    if (emit) {
      emit("update", {
        isValid: uploaded.value && !hasError.value && data.value.dataframeData && data.value.dataframeData.data.length > 0,
        fileName: data.value.fileName,
        dataframeData: data.value.dataframeData,
        rawContent: data.value.rawContent,
      });
    }
  };

  // File processing
  const processFile = async (file: File) => {
    // Reset state
    hasError.value = false;
    errorMessage.value = "";
    data.value = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
    };

    // Reset CSV state
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

    // Validate file type
    if (!fileService.isValidFileType(file, [".bib", ".bibtex", ".csv"])) {
      showError("Invalid file type. Please upload a .bib, .bibtex, or .csv file.");
      return;
    }

    data.value.fileName = file.name;

    try {
      // Read file content
      const content = await fileService.readFileContent(file);
      data.value.rawContent = content;

      if (isCsvFile(file)) {
        // Handle CSV file
        await parseCsvContent(content);
      } else if (isBibTexFile(file)) {
        // Handle BibTeX file
        data.value.dataframeData = await fileService.parseBibTeX(content);

        if (data.value.dataframeData && data.value.dataframeData.data.length > 0) {
          uploaded.value = true;
          if (emit) {
            emitUpdate();
          }
        } else {
          showError("No valid BibTeX entries found in the file.");
        }
      }
    } catch (error: any) {
      showError(`Failed to process file: ${error.message}`);
    }
  };

  const isCsvFile = (file: File): boolean => {
    return file.name.toLowerCase().endsWith(".csv");
  };

  const isBibTexFile = (file: File): boolean => {
    const fileName = file.name.toLowerCase();
    return fileName.endsWith(".bib") || fileName.endsWith(".bibtex");
  };

  const parseCsvContent = async (content: string) => {
    try {
      const previewData = await fileService.parseCSVForPreview(content);

      csvData.value = {
        rawData: previewData.rawData,
        columns: previewData.columns,
        previewRows: previewData.previewRows,
      };

      showCsvColumnSelection.value = true;
    } catch (error: any) {
      throw new Error(`CSV parsing failed: ${error.message}`);
    }
  };

  const processCsvWithConfig = async () => {
    try {
      if (!csvConfig.value.referenceColumn) {
        showError("Please select a reference column to continue.");
        return;
      }

      if (!csvData.value.rawData || csvData.value.rawData.length === 0) {
        showError("No CSV data available. Please upload a file first.");
        return;
      }

      data.value.dataframeData = await fileService.parseCSVWithConfig(
        csvData.value.rawData,
        csvConfig.value
      );

      showCsvColumnSelection.value = false;
      uploaded.value = true;
      if (emit) {
        emitUpdate();
      }
    } catch (error: any) {
      showError(`Failed to process CSV data: ${error.message}`);
    }
  };

  const handleCsvConfigUpdate = (config: CSVConfig) => {
    csvConfig.value = config;
  };

  const cancelCsvSelection = () => {
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

    data.value = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
    };
    uploaded.value = false;
    hasError.value = false;
    errorMessage.value = "";
  };

  const showError = (message: string) => {
    hasError.value = true;
    errorMessage.value = message;
    uploaded.value = false;
  };

  const clearError = () => {
    hasError.value = false;
    errorMessage.value = "";
  };

  const reset = () => {
    dragOver.value = false;
    uploaded.value = false;
    hasError.value = false;
    errorMessage.value = "";
    data.value = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
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
  };

  const initializeWithExistingData = () => {
    if (props.initialData && (props.initialData.fileName || (props.initialData.dataframeData && props.initialData.dataframeData.data.length > 0))) {
      data.value = {
        fileName: props.initialData.fileName || "",
        dataframeData: props.initialData.dataframeData || null,
        rawContent: props.initialData.rawContent || "",
      };
      uploaded.value = Boolean(data.value.dataframeData && data.value.dataframeData.data.length > 0);
      hasError.value = false;
      errorMessage.value = "";
      showCsvColumnSelection.value = false;
    }
  };

  // Watch for initial data changes
  watch(
    () => props.initialData,
    (newData) => {
      if (newData && (newData.fileName || (newData.dataframeData && newData.dataframeData.data.length > 0))) {
        initializeWithExistingData();
      }
    },
    { deep: true, immediate: true }
  );

  // Initialize on mount
  onMounted(() => {
    initializeWithExistingData();
  });

  return {
    // Reactive state
    dragOver,
    uploaded,
    hasError,
    errorMessage,
    data,
    showCsvColumnSelection,
    csvData,
    csvConfig,

    // Computed
    getDropzoneIcon,
    getDropzoneText,

    // Methods
    handleDragOver,
    handleDragLeave,
    handleDrop,
    triggerFileInput,
    handleFileSelect,
    fileInput,
    processFile,
    processCsvWithConfig,
    emitUpdate,
    handleCsvConfigUpdate,
    cancelCsvSelection,
    showError,
    clearError,
    reset,
    initializeWithExistingData,
  };
};