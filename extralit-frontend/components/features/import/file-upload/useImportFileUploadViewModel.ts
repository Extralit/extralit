/**
 * Shared view model for file upload components
 * Consolidates common upload logic with strategy pattern for file type-specific behavior
 */

import { ref, computed, watch, onMounted } from "@nuxtjs/composition-api";
import type {
  FileUploadState,
  FileUploadStrategy,
  FileUploadPayload,
} from "./types";

// Constants
export const FILE_UPLOAD_CONSTANTS = {
  MAX_PDF_SIZE: 200 * 1024 * 1024, // 200MB
  ACCEPTED_PDF_EXTENSIONS: [".pdf"],
  ACCEPTED_BIB_EXTENSIONS: [".bib", ".bibtex", ".csv"],
} as const;

export interface UseFileUploadOptions {
  strategy: FileUploadStrategy;
  initialData?: any;
  onUpdate?: (payload: FileUploadPayload) => void;
  hasValidData?: (data: any) => boolean;
  createPayload?: () => FileUploadPayload;
}

export const useImportFileUploadViewModel = (options: UseFileUploadOptions) => {
  const { strategy, initialData, onUpdate, hasValidData: customHasValidData, createPayload: customCreatePayload } = options;

  // Core reactive state
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

  // Additional reactive state for file data
  const data = ref<any>(initialData || {});

  // Computed properties
  const progressPercentage = computed(() => {
    if (state.value.totalFiles === 0) return 0;
    return Math.round((state.value.processedFiles / state.value.totalFiles) * 100);
  });

  const getDropzoneIcon = computed(() => {
    if (state.value.hasError) return "danger";
    if (state.value.uploaded) return "check";
    return strategy.getDropzoneIcon();
  });

  const getDropzoneText = computed(() => {
    if (state.value.hasError) return "Error processing files";
    if (state.value.uploaded) return strategy.getDropzoneText();
    return strategy.getDropzoneText();
  });

  // Drag and drop handlers
  const handleDragOver = (event: DragEvent) => {
    event.preventDefault();
    state.value.isDragging = true;
  };

  const handleDragLeave = () => {
    state.value.isDragging = false;
  };

  const handleDrop = (event: DragEvent) => {
    event.preventDefault();
    state.value.isDragging = false;

    const files = Array.from(event.dataTransfer?.files || []);
    processFiles(files);
  };

  // File processing
  const processFiles = async (files: File[]) => {
    // Reset error state
    state.value.hasError = false;
    state.value.errorMessage = "";
    state.value.processing = true;
    state.value.processedFiles = 0;
    state.value.totalFiles = files.length;

    try {
      // Use strategy for processing
      await strategy.processFiles(files);
      state.value.uploaded = true;
      state.value.hasError = false;
    } catch (error: any) {
      showError(error.message || "Failed to process files");
    } finally {
      state.value.processing = false;
    }

    // Emit update
    if (onUpdate && customCreatePayload) {
      onUpdate(createPayload());
    }
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

  // Reset functionality
  const reset = () => {
    state.value.isDragging = false;
    state.value.uploaded = false;
    state.value.hasError = false;
    state.value.errorMessage = "";
    state.value.processing = false;
    state.value.progress = 0;
    state.value.processedFiles = 0;
    state.value.totalFiles = 0;
    
    // Reset data to initial state
    data.value = initialData || {};
  };

  // Initialize with existing data
  const initializeWithExistingData = () => {
    if (initialData && hasValidData(initialData)) {
      data.value = { ...initialData };
      state.value.uploaded = true;
      state.value.hasError = false;
      state.value.errorMessage = "";
      state.value.processing = false;
    }
  };

  // Helper to check if data is valid (strategy-specific)
  const hasValidData = (data: any): boolean => {
    if (customHasValidData) {
      return customHasValidData(data);
    }
    // Default implementation
    return data && Object.keys(data).length > 0;
  };

  // Create payload for emission (strategy-specific)
  const createPayload = (): FileUploadPayload => {
    if (customCreatePayload) {
      return customCreatePayload();
    }
    // Default implementation - should be overridden
    throw new Error("createPayload must be implemented by strategy");
  };

  // Update progress (for strategies that need it)
  const updateProgress = (processed: number, total: number) => {
    state.value.processedFiles = processed;
    state.value.totalFiles = total;
    state.value.progress = total > 0 ? (processed / total) * 100 : 0;
  };

  // Watch for initial data changes
  watch(
    () => initialData,
    (newData) => {
      if (newData && hasValidData(newData)) {
        initializeWithExistingData();
      }
    },
    { deep: true, immediate: true }
  );

  // Initialize on mount
  onMounted(() => {
    if (initialData && hasValidData(initialData)) {
      initializeWithExistingData();
    }
  });

  return {
    // Reactive state
    state,
    data,

    // Computed properties
    progressPercentage,
    getDropzoneIcon,
    getDropzoneText,

    // Event handlers
    handleDragOver,
    handleDragLeave,
    handleDrop,

    // Core methods
    processFiles,
    showError,
    clearError,
    reset,
    initializeWithExistingData,
    updateProgress,

    // Helpers
    hasValidData,
    createPayload,
  };
};