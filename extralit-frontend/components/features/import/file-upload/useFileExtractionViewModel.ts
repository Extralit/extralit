/**
 * View model for FileExtraction component
 * Handles file content extraction using Extractous API
 */

import { ref, computed } from "@nuxtjs/composition-api";

export interface ExtractionResult {
  extracted_text: string;
  metadata: Record<string, any>;
  original_filename: string;
  content_type?: string;
  file_size?: number;
}

export const useFileExtractionViewModel = (props: any, { emit }: any) => {
  // State
  const selectedFile = ref<File | null>(null);
  const extracting = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");
  const extractionResult = ref<ExtractionResult | null>(null);

  // Computed
  const availableFiles = computed(() => {
    return props.availableFiles?.filter((file: File) => file.size > 0) || [];
  });

  // Methods
  const formatFileSize = (bytes: number | undefined): string => {
    if (!bytes) return "Unknown size";
    const sizes = ["Bytes", "KB", "MB", "GB"];
    if (bytes === 0) return "0 Bytes";
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + " " + sizes[i];
  };

  const getDetectedFormat = (metadata: Record<string, any>): string => {
    const contentType = metadata["Content-Type"];
    if (Array.isArray(contentType) && contentType.length > 0) {
      return contentType[0];
    }
    if (typeof contentType === "string") {
      return contentType;
    }
    return "Unknown";
  };

  const formatMetadata = (metadata: Record<string, any>): string => {
    return JSON.stringify(metadata, null, 2);
  };

  const extractFile = async (): Promise<void> => {
    if (!selectedFile.value) {
      return;
    }

    extracting.value = true;
    hasError.value = false;
    errorMessage.value = "";
    extractionResult.value = null;

    try {
      // Create FormData for file upload
      const formData = new FormData();
      formData.append("file", selectedFile.value);

      // Make API request to extraction endpoint
      const response = await fetch("/api/v1/extract", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const result = await response.json();
      extractionResult.value = result;

      // Emit extraction success event
      emit("extraction-success", {
        file: selectedFile.value,
        result: result,
      });

    } catch (error: any) {
      console.error("Extraction failed:", error);
      hasError.value = true;
      errorMessage.value = error.message || "Failed to extract file content";

      // Emit extraction error event
      emit("extraction-error", {
        file: selectedFile.value,
        error: error.message || "Unknown error",
      });
    } finally {
      extracting.value = false;
    }
  };

  const reset = (): void => {
    selectedFile.value = null;
    extracting.value = false;
    hasError.value = false;
    errorMessage.value = "";
    extractionResult.value = null;
  };

  const clearResult = (): void => {
    extractionResult.value = null;
    hasError.value = false;
    errorMessage.value = "";
  };

  return {
    // State
    selectedFile,
    extracting,
    hasError,
    errorMessage,
    extractionResult,

    // Computed
    availableFiles,

    // Methods
    formatFileSize,
    getDetectedFormat,
    formatMetadata,
    extractFile,
    reset,
    clearResult,
  };
};