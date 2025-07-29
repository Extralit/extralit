<template>
  <BaseFlowModal
    :visible="isVisible"
    :title="$t('import.title') || 'Import Documents'"
    :steps="steps"
    :current-step="currentStep"
    :can-go-back="canGoBack"
    :can-go-next="canGoNext"
    :can-complete="canComplete"
    :loading="isProcessing"
    :step-data="stepData"
    :confirm-close="true"
    @step-change="handleStepChange"
    @validate-step="handleValidateStep"
    @complete="handleComplete"
    @close="handleClose"
    @cancel="handleCancel"
  >
    <template #default="{ currentStep: stepIndex }">
      <!-- Step 1: Combined File Upload -->
      <ImportFileUpload
        v-if="stepIndex === 0"
        ref="fileUploadComponent"
        @bib-update="handleBibUpdate"
        @pdf-update="handlePdfUpdate"
      />

      <!-- Step 2: Import Analysis -->
      <ImportAnalysisTable
        v-if="stepIndex === 1"
        ref="analysisTableComponent"
        :analysis-data="analysisData"
        :loading="isAnalyzing"
        @update="handleAnalysisUpdate"
        @retry="performImportAnalysis"
      />

      <!-- Step 3: Upload Progress -->
      <ImportBatchProgress
        v-if="stepIndex === 2"
        ref="batchProgressComponent"
        :upload-data="uploadData"
        @completed="handleUploadCompleted"
        @cancelled="handleUploadCancelled"
        @error="handleUploadError"
      />

      <!-- Step 4: Import Summary -->
      <ImportSummary
        v-if="stepIndex === 3"
        ref="summaryComponent"
        :summary-data="summaryData"
        @return-to-library="handleReturnToLibrary"
        @view-import-history="handleViewImportHistory"
      />
    </template>
  </BaseFlowModal>
</template>

<script>
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/import";

export default {
  name: "ImportModal",

  props: {
    isVisible: {
      type: Boolean,
      default: false,
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
        parsedEntries: [],
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
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0,
      },
      summaryData: {
        totalProcessed: 0,
        successfullyAdded: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null,
      },

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
      return this.currentStep > 0 && this.currentStep < 2 && !this.isProcessing;
    },

    canGoNext() {
      switch (this.currentStep) {
        case 0:
          return this.bibData.parsedEntries.length > 0 && this.pdfData.matchedFiles.length > 0 && !this.hasError;
        case 1:
          return Object.keys(this.analysisData.documents).length > 0 && !this.hasError;
        default:
          return false;
      }
    },

    canComplete() {
      return this.currentStep === 3; // Only on summary step
    },

    stepData() {
      return {
        bibData: this.bibData,
        pdfData: this.pdfData,
        analysisData: this.analysisData,
        uploadData: this.uploadData,
        summaryData: this.summaryData,
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

      // Perform any necessary actions when entering a step
      if (newStep === 1) {
        this.performImportAnalysis();
      } else if (newStep === 2) {
        this.startImport();
      }
    },

    handleValidateStep({ step, callback }) {
      // Validate current step before allowing navigation
      let isValid = false;

      switch (step) {
        case 0:
          isValid = this.bibData.parsedEntries.length > 0 && this.pdfData.matchedFiles.length > 0 && !this.hasError;
          break;
        case 1:
          isValid = Object.keys(this.analysisData.documents).length > 0 && !this.hasError;
          break;
        default:
          isValid = true;
      }

      callback(isValid);
    },

    handleComplete() {
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
        parsedEntries: data.parsedEntries || [],
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
      this.clearError();
    },

    // Step 3: Analysis handlers
    async performImportAnalysis() {
      if (this.isAnalyzing) return;

      this.isAnalyzing = true;
      this.clearError();

      try {
        // Create analysis request from bib and PDF data
        const analysisRequest = this.createAnalysisRequest();

        // Call backend analysis API (placeholder for now)
        const response = await this.callImportAnalysisAPI(analysisRequest);

        this.analysisData = response;
      } catch (error) {
        this.showError(`Analysis failed: ${error.message}`, true);
      } finally {
        this.isAnalyzing = false;
      }
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

    handleUploadCompleted(summaryData) {
      this.summaryData = summaryData;
      this.isUploading = false;
      this.isProcessing = false;
      this.currentStep = 3; // Move to summary step
      this.clearError();
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
      this.handleClose();
      // Navigate to workspace documents (would be handled by parent)
      this.$emit("navigate-to-library");
    },

    handleViewImportHistory() {
      this.handleClose();
      // Navigate to import history (would be handled by parent)
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

      switch (this.currentStep) {
        case 0:
          if (this.$refs.fileUploadComponent) {
            this.$refs.fileUploadComponent.reset();
          }
          break;
        case 1:
          this.performImportAnalysis();
          break;
        case 2:
          this.startImport();
          break;
      }
    },

    // Modal lifecycle
    handleClose() {
      if (this.isUploading) {
        // Confirm before closing during upload
        if (confirm("Import is in progress. Are you sure you want to cancel?")) {
          this.cancelUpload();
          this.$emit("close");
        }
      } else {
        this.$emit("close");
      }
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
        parsedEntries: [],
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
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0,
      };
      this.summaryData = {
        totalProcessed: 0,
        successfullyAdded: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null,
      };

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

    // Placeholder API methods (to be implemented in future tasks)
    createAnalysisRequest() {
      // This will create the ImportAnalysisRequest from bibData and pdfData
      return {
        workspace_id: this.$route.params.id, // Assuming workspace ID from route
        documents: {}, // Will be populated from parsed data
      };
    },

    async callImportAnalysisAPI() {
      // Placeholder for actual API call
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            documents: {},
            summary: {
              total_documents: this.bibData.parsedEntries.length,
              add_count: Math.floor(this.bibData.parsedEntries.length * 0.7),
              update_count: Math.floor(this.bibData.parsedEntries.length * 0.2),
              skip_count: Math.floor(this.bibData.parsedEntries.length * 0.1),
              failed_count: 0,
            },
          });
        }, 1000);
      });
    },

    initializeUploadData() {
      // Initialize upload tracking data
      this.uploadData.totalBatches = Math.ceil(Object.keys(this.uploadData.confirmedDocuments).length / 20);
      this.uploadData.currentBatch = 0;
      this.uploadData.completedJobs = 0;
      this.uploadData.failedJobs = 0;
    },

    async startBatchUpload() {
      // Placeholder for batch upload logic
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            totalProcessed: this.bibData.parsedEntries.length,
            successfullyAdded: Math.floor(this.bibData.parsedEntries.length * 0.8),
            updated: Math.floor(this.bibData.parsedEntries.length * 0.15),
            skipped: Math.floor(this.bibData.parsedEntries.length * 0.05),
            failed: 0,
            errors: [],
            importId: "import_" + Date.now(),
          });
        }, 3000);
      });
    },
  },

  // Components are auto-imported by Nuxt
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
