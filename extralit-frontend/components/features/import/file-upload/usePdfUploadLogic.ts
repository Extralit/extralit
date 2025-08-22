/**
 * Helper composable for PdfUpload component
 * Gradual migration to Composition API while maintaining existing structure
 */

import { ref, watch, onMounted, computed } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import type { PdfData } from "./types";
import { PdfMatchingService } from "~/v1/domain/services/FileMatchingService";

export const FILE_UPLOAD_CONSTANTS = {
  MAX_PDF_SIZE: 200 * 1024 * 1024, // 200MB
  ACCEPTED_PDF_EXTENSIONS: [".pdf"] as string[],
  ACCEPTED_BIB_EXTENSIONS: [".bib", ".bibtex", ".csv"] as string[],
} as const;

export const usePdfUploadLogic = (
  props: {
    initialData: PdfData;
    bibliographyEntries: any;
  },
  emit?: (event: string, data: any) => void
) => {
  const pdfMatchingService = useResolve(PdfMatchingService);

  // Reactive state
  const dragOver = ref(false);
  const uploaded = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");
  const processing = ref(false);
  const processedFiles = ref(0);
  const totalFiles = ref(0);

  const data = ref<PdfData>({
    matchedFiles: [],
    unmatchedFiles: [],
    totalFiles: 0,
  });

  // Computed properties
  const progressPercentage = () => {
    if (totalFiles.value === 0) return 0;
    return Math.round((processedFiles.value / totalFiles.value) * 100);
  };

  const getDropzoneIcon = computed(() => {
    if (hasError.value) return "danger";
    if (uploaded.value) return "check";
    return "import";
  });

  const getDropzoneText = computed(() => {
    if (hasError.value) return "Error processing PDF files";
    if (uploaded.value) return "Upload PDF Files";
    return "Upload PDF Files";
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

    const files = Array.from(event.dataTransfer?.files || []);
    processFiles(files);
  };

  // File input handling
  const triggerFolderInput = () => {
    const folderInput = document.querySelector('input[type="file"][webkitdirectory]') as HTMLInputElement;
    if (folderInput) {
      folderInput.click();
    }
  };

  const handleFolderSelect = (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = Array.from(target.files || []);
    processFiles(files);
  };

  // File processing
  const processFiles = async (files: File[]) => {
    // Reset error state but preserve existing files for additive upload
    hasError.value = false;
    errorMessage.value = "";

    // Get existing files to merge with new ones
    const existingFiles = [...data.value.matchedFiles.map((mf) => mf.file), ...data.value.unmatchedFiles];

    processedFiles.value = 0;

    const pdfFiles = files.filter((file) => isValidPdfFile(file));

    if (pdfFiles.length === 0) {
      showError("No valid PDF files found. Please select a folder containing PDF files.");
      return;
    }

    totalFiles.value = pdfFiles.length;
    processing.value = true;
    clearError();

    const validFiles: File[] = [];
    const fileErrors: string[] = [];

    for (const file of pdfFiles) {
      // Skip files that are already uploaded (by name)
      const isDuplicate = existingFiles.some((existingFile) => existingFile.name === file.name);
      if (!isDuplicate) {
        const result = await validatePdfFile(file);
        if (result.valid) {
          validFiles.push(file);
        } else {
          fileErrors.push(`${file.name}: ${result.error}`);
        }
      }
      processedFiles.value++;
    }

    // Combine existing files with new valid files
    const allFiles = [...existingFiles, ...validFiles];
    data.value.totalFiles = allFiles.length;

    // Re-run file matching with all files (existing + new)
    performFileMatching(allFiles);

    processing.value = false;

    // Show errors if any files failed, but don't fail the entire process
    if (fileErrors.length > 0) {
      const successCount = validFiles.length;
      const errorCount = fileErrors.length;
      const totalCount = successCount + errorCount;

      let errorMsg = `Processed ${successCount} of ${totalCount} files successfully.\n\n`;
      errorMsg += `Files that could not be processed:\n${fileErrors.join("\n")}`;

      showError(errorMsg);
    } else {
      uploaded.value = true;
      hasError.value = false;
      errorMessage.value = "";
    }

    // Emit update if emit function is provided
    if (emit) {
      emitUpdate();
    }
  };

  // Watch for changes and emit updates
  const emitUpdate = () => {
    if (emit) {
      emit("update", {
        isValid: uploaded.value && !hasError.value && data.value.matchedFiles.length > 0,
        matchedFiles: data.value.matchedFiles,
        unmatchedFiles: data.value.unmatchedFiles,
        totalFiles: data.value.totalFiles,
        hasError: hasError.value,
        errorMessage: errorMessage.value,
      });
    }
  };

  const validatePdfFile = (file: File): { valid: boolean; error?: string } => {
    const maxSize = FILE_UPLOAD_CONSTANTS.MAX_PDF_SIZE;
    if (file.size > maxSize) {
      return { valid: false, error: `File ${file.name} is too large (max 200MB)` };
    } else if (file.size === 0) {
      return { valid: false, error: `File ${file.name} is empty` };
    }

    return { valid: true };
  };

  const isValidPdfFile = (file: File): boolean => {
    return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  };

  const performFileMatching = (uploadedFiles: File[]) => {
    if (
      !props.bibliographyEntries ||
      !props.bibliographyEntries.data ||
      props.bibliographyEntries.data.length === 0 ||
      uploadedFiles.length === 0
    ) {
      // If no bibliography entries, all files are unmatched
      data.value.matchedFiles = [];
      data.value.unmatchedFiles = uploadedFiles;
      return;
    }

    const result = pdfMatchingService.matchFiles(uploadedFiles, props.bibliographyEntries);

    data.value.matchedFiles = result.matchedFiles;
    data.value.unmatchedFiles = result.unmatchedFiles;
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
    processing.value = false;
    processedFiles.value = 0;
    totalFiles.value = 0;
    data.value = {
      matchedFiles: [],
      unmatchedFiles: [],
      totalFiles: 0,
    };
  };

  const initializeWithExistingData = () => {
    if (
      props.initialData &&
      (props.initialData.matchedFiles.length > 0 ||
        props.initialData.unmatchedFiles.length > 0 ||
        props.initialData.totalFiles > 0)
    ) {
      data.value = {
        matchedFiles: props.initialData.matchedFiles || [],
        unmatchedFiles: props.initialData.unmatchedFiles || [],
        totalFiles: props.initialData.totalFiles || 0,
      };
      uploaded.value = data.value.totalFiles > 0;
      hasError.value = false;
      errorMessage.value = "";
      processing.value = false;
    }
  };

  // Watch for initial data changes
  watch(
    () => props.initialData,
    (newData) => {
      if (newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0 || newData.totalFiles > 0)) {
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
    processing,
    processedFiles,
    totalFiles,
    data,

    // Computed
    progressPercentage,
    getDropzoneIcon,
    getDropzoneText,

    // Methods
    handleDragOver,
    handleDragLeave,
    handleDrop,
    triggerFolderInput,
    handleFolderSelect,
    processFiles,
    emitUpdate,
    showError,
    clearError,
    reset,
    initializeWithExistingData,
  };
};
