<template>
  <BaseFlowModal :visible="isVisible" :title="$t('import.title', { workspaceName: workspace?.name })" :steps="steps"
    :current-step="currentStep" :can-go-back="canGoBack" :can-go-next="canGoNext" :can-complete="canComplete"
    :loading="isProcessing" :step-data="stepData" :confirm-close="shouldConfirmClose" :submit-step-index="1"
    @step-change="handleStepChange" @validate-step="handleValidateStep" @complete="handleComplete" @close="handleClose"
    @cancel="handleCancel">
    <template #default="{ currentStep: stepIndex }">
      <!-- Step 1: PDF First, then Optional Table Upload -->
      <ImportFileUpload v-if="stepIndex === 0" ref="fileUploadComponent" :initial-bib-data="bibData"
        :initial-pdf-data="pdfData" @bib-update="handleBibUpdate" @pdf-update="handlePdfUpdate" />

      <!-- Step 2: Import Analysis -->
      <ImportAnalysisTable v-if="stepIndex === 1" ref="analysisTableComponent" :dataframe-data="bibData.dataframeData"
        :pdf-data="pdfData" :workspace="workspace" :loading="isAnalyzing" @update="handleAnalysisUpdate"
        @analysis-complete="handleAnalysisComplete" />

      <!-- Step 3: Upload Progress -->
      <ImportBatchProgress v-if="stepIndex === 2" ref="batchProgressComponent" :upload-data="uploadData"
        :workspace="workspace" :dataframe-data="bibData.dataframeData" :bib-file-name="bibData.fileName"
        :pdf-files="getAllPdfFiles()" @completed="handleUploadCompleted" @cancelled="handleUploadCancelled"
        @error="handleUploadError" @progress="handleUploadProgress" />

      <!-- Step 4: Import Summary -->
      <ImportSummary v-if="stepIndex === 3" ref="summaryComponent" :import-summary="importSummary"
        :workspace="workspace" :bibFileName="bibData.fileName" :failed-documents="failedDocuments"
        @return-to-library="handleReturnToLibrary" @view-import-history="handleViewImportHistory" />
    </template>
  </BaseFlowModal>
</template>

<script lang="ts">
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/import";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";

export default {
  name: "ImportFlow",

  props: {
    isVisible: {
      type: Boolean,
      default: false,
    },
    workspace: {
      type: Workspace,
      default: null,
    },
  },

  data() {
    return {
      currentStep: 0,
      totalSteps: 4,
      isProcessing: false,
      isAnalyzing: false,
      isUploading: false,
      hasError: false,
      errorMessage: "",
      canRetryError: false,

      // Step data
      bibData: {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      },
      pdfData: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      },
      analysisData: {
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0,
        },
      },
      uploadData: {
        confirmedDocuments: {},
        documentActions: {}, // Track original analysis statuses
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0,
      },
      importSummary: {
        total: 0,
        added: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null,
      },
      failedDocuments: [],

      // Step definitions
      steps: [
        {
          id: "file-upload",
          title: "Upload Files",
        },
        {
          id: "analysis",
          title: "Review Import",
        },
        {
          id: "progress",
          title: "Import Progress",
        },
        {
          id: "summary",
          title: "Import Summary",
        },
      ],
    };
  },

  computed: {
    canGoBack() {
      // Allow going back from step 1 to step 0, but not during upload or from later steps
      return this.currentStep > 0 && this.currentStep <= 1 && !this.isProcessing && !this.isUploading;
    },

    canGoNext() {
      switch (this.currentStep) {
        case 0:
          return (
            this.pdfData &&
            this.pdfData.totalFiles > 0 &&
            !this.hasError &&
            !!this.workspace
          );
        case 1:
          return Object.keys(this.uploadData.confirmedDocuments).length > 0 && !this.hasError && !!this.workspace;
        case 2:
          // Can't go next from upload progress step - must wait for completion
          return false;
        default:
          return false;
      }
    },

    canComplete() {
      return this.currentStep === 3; // Only on summary step
    },

    shouldConfirmClose() {
      // Only require confirmation during the import process (steps 0-2)
      // After successful completion (step 3), allow closing without confirmation
      return this.currentStep < 3 && (this.isProcessing || this.isUploading || this.hasDataToLose());
    },

    stepData() {
      return {
        bibData: this.bibData,
        pdfData: this.pdfData,
        analysisData: this.analysisData,
        uploadData: this.uploadData,
        importSummary: this.importSummary,
      };
    },
  },

  watch: {
    isVisible(newValue) {
      if (newValue) {
        this.resetModal();
      }
    },
  },

  methods: {
    // Flow modal event handlers
    handleStepChange(newStep) {
      this.currentStep = newStep;
      this.clearError();

      // Ensure component refs are updated after step change
      this.$nextTick(() => {
        // If going back to step 0, ensure the file upload component is properly initialized
        if (newStep === 0 && this.$refs.fileUploadComponent) {
          // The component will auto-initialize with the provided props
        }
      });
    },

    handleValidateStep({ step, callback }) {
      // Validate current step before allowing navigation
      let isValid = false;

      switch (step) {
        case 0:
          isValid =
            this.pdfData &&
            this.pdfData.totalFiles > 0 &&
            !this.hasError &&
            !!this.workspace;
          break;

        case 1:
          isValid = Object.keys(this.uploadData.confirmedDocuments).length > 0 && !this.hasError && !!this.workspace;

          // If moving to step 2 (upload progress), start the upload process
          if (isValid && step === 1) {
            this.$nextTick(() => {
              // The ImportBatchProgress component will auto-start when it receives uploadData
              this.isUploading = true;
              this.isProcessing = true;
            });
          }
          break;
        default:
          isValid = true;
      }

      callback(isValid);
    },

    handleComplete() {
      // Emit import completed event before closing
      this.$emit("import-completed");
      this.handleReturnToLibrary();
    },

    handleCancel() {
      if (this.isUploading) {
        this.cancelUpload();
      }
      this.$emit("close");
    },

    // Step handlers
    handleBibUpdate(data) {
      this.bibData = {
        fileName: data.fileName || "",
        dataframeData: data.dataframeData || null,
        rawContent: data.rawContent || "",
      };
      this.clearError();
    },

    handlePdfUpdate(data) {
      this.pdfData = {
        matchedFiles: data.matchedFiles || [],
        unmatchedFiles: data.unmatchedFiles || [],
        totalFiles: data.totalFiles || 0,
      };
      this.clearError();
    },

    handleAnalysisUpdate(data) {
      this.uploadData.confirmedDocuments = data.confirmedDocuments || {};
      this.uploadData.documentActions = data.documentActions || {}; // Store the original analysis statuses

      // Update bibData with filtered dataframe data if provided
      if (data.filteredDataframeData) {
        this.bibData.dataframeData = data.filteredDataframeData;
      }

      this.clearError();
    },

    handleUploadProgress(progressData) {
      // Update upload data with progress information
      this.uploadData.currentBatch = progressData.currentBatch || 0;
      this.uploadData.totalBatches = progressData.totalBatches || 0;
      this.uploadData.completedJobs = progressData.completedJobs || 0;
      this.uploadData.failedJobs = progressData.failedJobs || 0;
    },

    handleAnalysisComplete(analysisData) {
      this.analysisData = analysisData;
      this.clearError();
    },

    async startImport() {
      if (Object.keys(this.uploadData.confirmedDocuments).length === 0) return;

      this.isUploading = true;
      this.isProcessing = true;
      this.clearError();

      try {
        // Initialize upload data
        this.initializeUploadData();

        // Start batch upload process (placeholder for now)
        await this.startBatchUpload();
      } catch (error) {
        this.showError(`Import failed: ${error.message}`, true);
        this.isUploading = false;
        this.isProcessing = false;
      }
    },

    handleUploadCompleted(uploadResult) {
      this.importSummary = uploadResult.importSummary;
      this.failedDocuments = uploadResult.failedDocuments || [];
      this.isUploading = false;
      this.isProcessing = false;
      this.clearError();

      // Automatically move to summary step
      this.$nextTick(() => {
        this.currentStep = 3;
      });
    },

    handleUploadCancelled() {
      this.isUploading = false;
      this.isProcessing = false;
      this.showError("Import was cancelled by user", false);
    },

    handleUploadError(error) {
      this.isUploading = false;
      this.isProcessing = false;
      this.showError(`Upload failed: ${error.message}`, true);
    },

    cancelUpload() {
      if (this.$refs.batchProgressComponent) {
        this.$refs.batchProgressComponent.cancelUpload();
      }
    },

    // Step 5: Summary handlers
    handleReturnToLibrary() {
      // Emit import completed event before closing
      this.$emit("import-completed");
      this.$emit("close");
      // TODO: Navigate to workspace documents (would be handled by parent)
      this.$emit("navigate-to-library");
    },

    handleViewImportHistory() {
      // Emit import completed event before closing
      this.$emit("import-completed");
      this.$emit("close");
      // TODO: Navigate to import history (would be handled by parent)
      this.$emit("navigate-to-import-history");
    },

    // Error handling
    handleValidationError(error) {
      this.showError(error.message || error, true);
    },

    showError(message, canRetry = false) {
      this.hasError = true;
      this.errorMessage = message;
      this.canRetryError = canRetry;
    },

    clearError() {
      this.hasError = false;
      this.errorMessage = "";
      this.canRetryError = false;
    },

    retryCurrentStep() {
      this.clearError();

    },

    handleClose() {
      // If we're on the summary step (step 3), emit refresh event before closing
      if (this.currentStep === 3) {
        this.$emit("import-completed");
      }

      this.$emit("close");
    },

    hasDataToLose() {
      // Check if user has uploaded any data that would be lost on close
      const analysisTable = this.$refs.analysisTableComponent;
      return (
        (this.bibData.dataframeData && this.bibData.dataframeData.data && this.bibData.dataframeData.data.length > 0) ||
        this.pdfData.totalFiles > 0 ||
        Object.keys(this.uploadData.confirmedDocuments).length > 0 ||
        (analysisTable && analysisTable.editableTableData && analysisTable.editableTableData.length > 0)
      );
    },

    resetModal() {
      this.currentStep = 0;
      this.isProcessing = false;
      this.isAnalyzing = false;
      this.isUploading = false;
      this.clearError();

      // Reset all step data
      this.bibData = {
        fileName: "",
        dataframeData: null,
        rawContent: "",
      };
      this.pdfData = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0,
      };
      this.analysisData = {
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0,
        },
      };
      this.uploadData = {
        confirmedDocuments: {},
        documentActions: {},
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0,
      };
      this.importSummary = {
        total: 0,
        added: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null,
      };
      this.failedDocuments = [];

      // Reset child components
      this.$nextTick(() => {
        if (this.$refs.fileUploadComponent) {
          this.$refs.fileUploadComponent.reset();
        }
        if (this.$refs.analysisTableComponent) {
          this.$refs.analysisTableComponent.reset();
        }
        if (this.$refs.batchProgressComponent) {
          this.$refs.batchProgressComponent.reset();
        }
        if (this.$refs.summaryComponent) {
          this.$refs.summaryComponent.reset();
        }
      });
    },


    initializeUploadData() {
      // Initialize upload tracking data
      this.uploadData.totalBatches = Math.ceil(Object.keys(this.uploadData.confirmedDocuments).length / 20);
      this.uploadData.currentBatch = 0;
      this.uploadData.completedJobs = 0;
      this.uploadData.failedJobs = 0;
    },

    getAllPdfFiles() {
      // Collect all PDF files from both matched and unmatched files
      const files = [];

      // Add matched files
      if (this.pdfData.matchedFiles) {
        this.pdfData.matchedFiles.forEach(matchedFile => {
          if (matchedFile.file) {
            files.push(matchedFile.file);
          }
        });
      }

      // Add unmatched files
      if (this.pdfData.unmatchedFiles) {
        this.pdfData.unmatchedFiles.forEach(unmatchedFile => {
          // Unmatched files are stored directly as File objects
          if (unmatchedFile instanceof File) {
            files.push(unmatchedFile);
          }
        });
      }

      return files;
    },

    async startBatchUpload() {
      // The actual batch upload is now handled by ImportBatchProgress component
      // This method is kept for compatibility but the real work happens in the component
      return new Promise<void>((resolve) => {
        // The ImportBatchProgress component will handle the upload and emit completion
        resolve();
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.import-modal__error {
  display: flex;
  align-items: flex-start;
  gap: $base-space;
  padding: $base-space * 2;
  background: var(--bg-banner-error);
  border: 1px solid var(--color-danger);
  border-radius: $border-radius;
  margin-top: $base-space * 2;
}

.import-modal__error-icon {
  color: var(--color-danger);
  font-size: 1.2rem;
  margin-top: 0.1rem;
  flex-shrink: 0;
}

.import-modal__error-content {
  flex: 1;

  h4 {
    margin: 0 0 $base-space 0;
    color: var(--color-danger);
    font-weight: 600;
    font-size: 1rem;
  }

  p {
    margin: 0 0 $base-space 0;
    color: var(--fg-primary);
    font-size: 0.9rem;
  }
}
</style>
