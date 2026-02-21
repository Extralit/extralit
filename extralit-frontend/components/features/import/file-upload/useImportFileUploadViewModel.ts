/**
 * View model for ImportFileUpload component
 * Handles coordination between bibliography and PDF uploads
 */

import { ref, computed, watch, nextTick } from "@nuxtjs/composition-api";
import type { BibliographyData, PdfData } from "./types";

export const useImportFileUploadViewModel = (props: any, { emit }: any) => {
  // Internal flag to prevent recursive updates during initialization
  const isInitializing = ref(false);

  // Bibliography data
  const bibData = ref<BibliographyData>({
    fileName: "",
    dataframeData: null,
    rawContent: "",
  });

  // PDF data
  const pdfData = ref<PdfData>({
    matchedFiles: [],
    unmatchedFiles: [],
    totalFiles: 0,
  });

  // Computed properties
  const isValid = computed(() => {
    return pdfData.value.totalFiles > 0;
  });

  // Event handlers
  const handleBibUpdate = (data: any) => {
    bibData.value = {
      fileName: data.fileName || "",
      dataframeData: data.dataframeData || null,
      rawContent: data.rawContent || "",
    };

    emitBibUpdate();
  };

  const handlePdfUpdate = (data: any) => {
    pdfData.value = {
      matchedFiles: data.matchedFiles || [],
      unmatchedFiles: data.unmatchedFiles || [],
      totalFiles: data.totalFiles || 0,
    };

    // Update dataframe data with matched file paths
    updateDataframeWithFilePaths(data.matchedFiles || []);

    emitPdfUpdate();
  };

  // Event emitters
  const emitBibUpdate = () => {
    emit("bib-update", {
      isValid: true, // table optional, always valid
      fileName: bibData.value.fileName,
      dataframeData: bibData.value.dataframeData,
      rawContent: bibData.value.rawContent,
    });
  };

  const emitPdfUpdate = () => {
    emit("pdf-update", {
      isValid: pdfData.value.totalFiles > 0,
      matchedFiles: pdfData.value.matchedFiles,
      unmatchedFiles: pdfData.value.unmatchedFiles,
      totalFiles: pdfData.value.totalFiles,
    });
  };

  const updateDataframeWithFilePaths = (matchedFiles: any[]) => {
    if (!bibData.value.dataframeData || !matchedFiles.length) {
      return;
    }

    // Ensure the dataframeData has the expected structure
    if (!bibData.value.dataframeData.data || !Array.isArray(bibData.value.dataframeData.data)) {
      console.error('ImportFileUpload: Invalid dataframeData structure', bibData.value.dataframeData);
      return;
    }

    // Create a map of reference to file paths
    const referenceToFiles = new Map<string, string[]>();

    matchedFiles.forEach((matchedFile: any) => {
      const reference = matchedFile.bibEntry?.reference;
      const fileName = matchedFile.file?.name;

      if (reference && fileName) {
        if (!referenceToFiles.has(reference)) {
          referenceToFiles.set(reference, []);
        }
        referenceToFiles.get(reference)!.push(fileName);
      }
    });

    // Update the dataframe data with file paths
    const updatedData = bibData.value.dataframeData.data.map((row: any) => {
      const reference = row.reference || row.key;
      const filePaths = referenceToFiles.get(reference) || [];

      return {
        ...row,
        filePaths
      };
    });

    // Preserve the original structure while updating data
    bibData.value.dataframeData = {
      ...bibData.value.dataframeData,
      data: updatedData
    };

    // Re-emit the bib update with the updated dataframe
    emitBibUpdate();
  };

  // Initialize component with existing data when navigating back
  const initializeWithExistingData = () => {
    // Set flag to prevent recursive updates
    isInitializing.value = true;

    // Initialize bibliography data
    if (props.initialBibData && (props.initialBibData.fileName || (props.initialBibData.dataframeData && props.initialBibData.dataframeData.data.length > 0))) {
      bibData.value = {
        fileName: props.initialBibData.fileName || "",
        dataframeData: props.initialBibData.dataframeData || null,
        rawContent: props.initialBibData.rawContent || "",
      };
    }

    // Initialize PDF data
    if (props.initialPdfData && (props.initialPdfData.matchedFiles.length > 0 || props.initialPdfData.unmatchedFiles.length > 0 || props.initialPdfData.totalFiles > 0)) {
      pdfData.value = {
        matchedFiles: props.initialPdfData.matchedFiles || [],
        unmatchedFiles: props.initialPdfData.unmatchedFiles || [],
        totalFiles: props.initialPdfData.totalFiles || 0,
      };
    }

    // Clear the initialization flag and emit updates after all data is set
    nextTick(() => {
      isInitializing.value = false;
      // Emit updates to parent to ensure consistency
      emitBibUpdate();
      emitPdfUpdate();
    });
  };

  // Public methods for parent components
  const reset = () => {
    // Set flag to prevent recursive updates during reset
    isInitializing.value = true;

    // Reset bibliography data
    bibData.value = {
      fileName: "",
      dataframeData: null,
      rawContent: "",
    };

    // Reset PDF data
    pdfData.value = {
      matchedFiles: [],
      unmatchedFiles: [],
      totalFiles: 0,
    };

    // Clear the initialization flag and emit updates after reset
    nextTick(() => {
      isInitializing.value = false;
      emitBibUpdate();
      emitPdfUpdate();
    });
  };

  // Watch for initial data changes
  watch(
    () => props.initialBibData,
    (newData: any, oldData: any) => {
      // Only initialize if data has actually changed and we're not already initializing
      if (!isInitializing.value && newData && (newData.fileName || (newData.dataframeData && newData.dataframeData.data.length > 0))) {
        // Check if the data is actually different to avoid unnecessary updates
        const hasChanged = !oldData ||
          newData.fileName !== oldData.fileName ||
          (newData.dataframeData?.data?.length || 0) !== (oldData.dataframeData?.data?.length || 0);

        if (hasChanged) {
          initializeWithExistingData();
        }
      }
    },
    { deep: true, immediate: true }
  );

  watch(
    () => props.initialPdfData,
    (newData: any, oldData: any) => {
      // Only initialize if data has actually changed and we're not already initializing
      if (!isInitializing.value && newData && (newData.matchedFiles.length > 0 || newData.unmatchedFiles.length > 0)) {
        // Check if the data is actually different to avoid unnecessary updates
        const hasChanged = !oldData ||
          newData.matchedFiles.length !== oldData.matchedFiles.length ||
          newData.unmatchedFiles.length !== oldData.unmatchedFiles.length ||
          newData.totalFiles !== oldData.totalFiles;

        if (hasChanged) {
          initializeWithExistingData();
        }
      }
    },
    { deep: true, immediate: true }
  );

  return {
    // Reactive state
    isInitializing,
    bibData,
    pdfData,

    // Computed
    isValid,

    // Methods
    handleBibUpdate,
    handlePdfUpdate,
    emitBibUpdate,
    emitPdfUpdate,
    updateDataframeWithFilePaths,
    initializeWithExistingData,
    reset,
  };
};
