<template>
  <div v-if="isVisible"
    style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: red; color: white; padding: 20px; font-size: 24px; z-index: 99999; border: 3px solid yellow;">
    TEST MODAL - isVisible: {{ isVisible }}
    <button @click="$emit('close')"
      style="margin-left: 20px; background: white; color: black; padding: 5px;">Close</button>
  </div>
</template>

<script>
import "assets/icons/check";
import "assets/icons/danger";
import "assets/icons/import";

export default {
  name: 'ImportModal',

  props: {
    isVisible: {
      type: Boolean,
      default: false
    }
  },

  watch: {
    isVisible(newValue) {
      console.log('ImportModal isVisible changed to:', newValue);
      if (newValue) {
        this.resetModal()
      }
    }
  },

  mounted() {
    console.log('ImportModal mounted, isVisible:', this.isVisible);
  },

  updated() {
    console.log('ImportModal updated, isVisible:', this.isVisible);
  },

  data() {
    return {
      currentStep: 1,
      totalSteps: 5,
      isProcessing: false,
      isAnalyzing: false,
      isUploading: false,
      hasError: false,
      errorMessage: '',
      canRetryError: false,

      // Step data
      bibData: {
        fileName: '',
        parsedEntries: [],
        dataframeData: null,
        rawContent: ''
      },
      pdfData: {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0
      },
      analysisData: {
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0
        }
      },
      uploadData: {
        confirmedDocuments: {},
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0
      },
      summaryData: {
        totalProcessed: 0,
        successfullyAdded: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null
      },

      // Step definitions
      steps: [
        {
          id: 'bib-upload',
          title: 'Upload Bibliography',
          description: 'Upload your .bib file with reference metadata'
        },
        {
          id: 'pdf-upload',
          title: 'Upload PDFs',
          description: 'Upload PDF files and match them to references'
        },
        {
          id: 'analysis',
          title: 'Review Import',
          description: 'Review and confirm which documents to import'
        },
        {
          id: 'progress',
          title: 'Import Progress',
          description: 'Track the progress of your document import'
        },
        {
          id: 'summary',
          title: 'Import Summary',
          description: 'View the results of your import operation'
        }
      ]
    }
  },

  computed: {
    progressPercentage() {
      return Math.round((this.currentStep / this.totalSteps) * 100)
    },

    canProceedFromStep1() {
      return this.bibData.parsedEntries.length > 0 && !this.hasError
    },

    canProceedFromStep2() {
      return this.pdfData.matchedFiles.length > 0 && !this.hasError
    },

    canProceedFromStep3() {
      return Object.keys(this.analysisData.documents).length > 0 && !this.hasError
    }
  },

  watch: {
    isVisible(newValue) {
      if (newValue) {
        this.resetModal()
      }
    }
  },

  methods: {
    // Navigation methods
    goToNextStep() {
      if (this.currentStep < this.totalSteps && this.canProceedToNextStep()) {
        this.currentStep++
        this.clearError()
        this.handleStepEntered()
      }
    },

    goToPreviousStep() {
      if (this.currentStep > 1 && this.currentStep < 4) {
        this.currentStep--
        this.clearError()
      }
    },

    canProceedToNextStep() {
      switch (this.currentStep) {
        case 1:
          return this.canProceedFromStep1
        case 2:
          return this.canProceedFromStep2
        case 3:
          return this.canProceedFromStep3
        default:
          return false
      }
    },

    handleStepEntered() {
      // Perform any necessary actions when entering a step
      if (this.currentStep === 3) {
        this.performImportAnalysis()
      }
    },

    // Step 1: Bibliography Upload handlers
    handleBibFileParsed(data) {
      this.bibData = {
        fileName: data.fileName,
        parsedEntries: data.parsedEntries,
        dataframeData: data.dataframeData,
        rawContent: data.rawContent
      }
      this.clearError()
    },

    // Step 2: PDF Upload handlers
    handlePdfFilesMatched(data) {
      this.pdfData = {
        matchedFiles: data.matchedFiles,
        unmatchedFiles: data.unmatchedFiles,
        totalFiles: data.totalFiles
      }
      this.clearError()
    },

    // Step 3: Analysis handlers
    async performImportAnalysis() {
      if (this.isAnalyzing) return

      this.isAnalyzing = true
      this.clearError()

      try {
        // Create analysis request from bib and PDF data
        const analysisRequest = this.createAnalysisRequest()

        // Call backend analysis API (placeholder for now)
        const response = await this.callImportAnalysisAPI(analysisRequest)

        this.analysisData = response
      } catch (error) {
        this.showError(`Analysis failed: ${error.message}`, true)
      } finally {
        this.isAnalyzing = false
      }
    },

    handleAnalysisConfirmed(confirmedDocuments) {
      this.uploadData.confirmedDocuments = confirmedDocuments
      this.clearError()
    },

    // Step 4: Upload handlers
    async startImport() {
      if (!this.canProceedFromStep3) return

      this.currentStep = 4
      this.isUploading = true
      this.clearError()

      try {
        // Initialize upload data
        this.initializeUploadData()

        // Start batch upload process (placeholder for now)
        await this.startBatchUpload()
      } catch (error) {
        this.showError(`Import failed: ${error.message}`, true)
        this.isUploading = false
      }
    },

    handleUploadCompleted(summaryData) {
      this.summaryData = summaryData
      this.isUploading = false
      this.currentStep = 5
      this.clearError()
    },

    handleUploadCancelled() {
      this.isUploading = false
      this.showError('Import was cancelled by user', false)
    },

    handleUploadError(error) {
      this.isUploading = false
      this.showError(`Upload failed: ${error.message}`, true)
    },

    cancelUpload() {
      if (this.$refs.batchProgressComponent) {
        this.$refs.batchProgressComponent.cancelUpload()
      }
    },

    // Step 5: Summary handlers
    handleReturnToLibrary() {
      this.handleClose()
      // Navigate to workspace documents (would be handled by parent)
      this.$emit('navigate-to-library')
    },

    handleViewImportHistory() {
      this.handleClose()
      // Navigate to import history (would be handled by parent)
      this.$emit('navigate-to-import-history')
    },

    // Error handling
    handleValidationError(error) {
      this.showError(error.message || error, true)
    },

    showError(message, canRetry = false) {
      this.hasError = true
      this.errorMessage = message
      this.canRetryError = canRetry
    },

    clearError() {
      this.hasError = false
      this.errorMessage = ''
      this.canRetryError = false
    },

    retryCurrentStep() {
      this.clearError()

      switch (this.currentStep) {
        case 1:
          if (this.$refs.bibUploadComponent) {
            this.$refs.bibUploadComponent.reset()
          }
          break
        case 2:
          if (this.$refs.pdfUploadComponent) {
            this.$refs.pdfUploadComponent.reset()
          }
          break
        case 3:
          this.performImportAnalysis()
          break
        case 4:
          this.startImport()
          break
      }
    },

    // Modal lifecycle
    handleClose() {
      if (this.isUploading) {
        // Confirm before closing during upload
        if (confirm('Import is in progress. Are you sure you want to cancel?')) {
          this.cancelUpload()
          this.$emit('close')
        }
      } else {
        this.$emit('close')
      }
    },

    resetModal() {
      this.currentStep = 1
      this.isProcessing = false
      this.isAnalyzing = false
      this.isUploading = false
      this.clearError()

      // Reset all step data
      this.bibData = {
        fileName: '',
        parsedEntries: [],
        dataframeData: null,
        rawContent: ''
      }
      this.pdfData = {
        matchedFiles: [],
        unmatchedFiles: [],
        totalFiles: 0
      }
      this.analysisData = {
        documents: {},
        summary: {
          total_documents: 0,
          add_count: 0,
          update_count: 0,
          skip_count: 0,
          failed_count: 0
        }
      }
      this.uploadData = {
        confirmedDocuments: {},
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0
      }
      this.summaryData = {
        totalProcessed: 0,
        successfullyAdded: 0,
        updated: 0,
        skipped: 0,
        failed: 0,
        errors: [],
        importId: null
      }

      // Reset child components
      this.$nextTick(() => {
        if (this.$refs.bibUploadComponent) {
          this.$refs.bibUploadComponent.reset()
        }
        if (this.$refs.pdfUploadComponent) {
          this.$refs.pdfUploadComponent.reset()
        }
        if (this.$refs.analysisTableComponent) {
          this.$refs.analysisTableComponent.reset()
        }
        if (this.$refs.batchProgressComponent) {
          this.$refs.batchProgressComponent.reset()
        }
        if (this.$refs.summaryComponent) {
          this.$refs.summaryComponent.reset()
        }
      })
    },

    // Placeholder API methods (to be implemented in future tasks)
    createAnalysisRequest() {
      // This will create the ImportAnalysisRequest from bibData and pdfData
      return {
        workspace_id: this.$route.params.id, // Assuming workspace ID from route
        documents: {} // Will be populated from parsed data
      }
    },

    async callImportAnalysisAPI(request) {
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
              failed_count: 0
            }
          })
        }, 1000)
      })
    },

    initializeUploadData() {
      // Initialize upload tracking data
      this.uploadData.totalBatches = Math.ceil(
        Object.keys(this.uploadData.confirmedDocuments).length / 20
      )
      this.uploadData.currentBatch = 0
      this.uploadData.completedJobs = 0
      this.uploadData.failedJobs = 0
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
            importId: 'import_' + Date.now()
          })
        }, 3000)
      })
    }
  },

  // Dynamic component imports (these will be created in future tasks)
  components: {
    BaseSpinner: () => import('@/components/base/base-spinner/BaseSpinner.vue'),
    ImportBibUpload: () => import('./ImportBibUpload.vue').catch(() => ({ template: '<div>ImportBibUpload component not yet implemented</div>' })),
    ImportPdfUpload: () => import('./ImportPdfUpload.vue').catch(() => ({ template: '<div>ImportPdfUpload component not yet implemented</div>' })),
    ImportAnalysisTable: () => import('./ImportAnalysisTable.vue').catch(() => ({ template: '<div>ImportAnalysisTable component not yet implemented</div>' })),
    ImportBatchProgress: () => import('./ImportBatchProgress.vue').catch(() => ({ template: '<div>ImportBatchProgress component not yet implemented</div>' })),
    ImportSummary: () => import('./ImportSummary.vue').catch(() => ({ template: '<div>ImportSummary component not yet implemented</div>' }))
  }
}
</script>

<style lang="scss" scoped>
.import-modal {
  max-width: 1200px !important;
  width: 90vw !important;
  max-height: 90vh !important;
  padding: 0 !important;
  overflow: hidden;
}

.import-modal__container {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 90vh;
}

.import-modal__header {
  padding: $base-space * 4 $base-space * 4 $base-space * 2 $base-space * 4;
  border-bottom: 1px solid var(--border-color);
  text-align: center;
}

.import-modal__title {
  @include font-size(32px);
  @include line-height(40px);
  font-weight: 600;
  margin: 0 0 $base-space 0;
  color: var(--fg-primary);
}

.import-modal__subtitle {
  @include font-size(16px);
  @include line-height(24px);
  color: var(--fg-secondary);
  margin: 0;
}

.import-modal__steps {
  display: flex;
  justify-content: space-between;
  padding: $base-space * 3 $base-space * 4;
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-secondary);
  overflow-x: auto;
}

.import-modal__step {
  display: flex;
  align-items: center;
  gap: $base-space + 2px;
  min-width: 200px;
  opacity: 0.5;
  transition: $swift-ease-out;

  &--active,
  &--completed {
    opacity: 1;
  }

  &--active {
    .import-modal__step-title {
      color: var(--primary-color);
      font-weight: 600;
    }
  }

  &--completed {
    .import-modal__step-title {
      color: var(--success-color);
    }
  }
}

.import-modal__step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: $base-space * 4;
  height: $base-space * 4;
  border-radius: $border-radius-rounded;
  background: var(--bg-tertiary);
  border: 2px solid var(--border-color);
  flex-shrink: 0;
  transition: $swift-ease-out;

  .import-modal__step--active & {
    background: var(--primary-color);
    border-color: var(--primary-color);
  }

  .import-modal__step--completed & {
    background: var(--success-color);
    border-color: var(--success-color);
  }
}

.import-modal__step-number {
  @include font-size(14px);
  @include line-height(18px);
  font-weight: 600;
  color: var(--fg-secondary);

  &--active {
    color: white;
  }
}

.import-modal__step-icon {
  font-size: 1rem;

  &--completed {
    color: white;
  }
}

.import-modal__step-content {
  flex: 1;
  min-width: 0;
}

.import-modal__step-title {
  @include font-size(14px);
  @include line-height(18px);
  font-weight: 500;
  margin: 0 0 calc($base-space / 2) 0;
  color: var(--fg-primary);
  transition: $swift-ease-out;
}

.import-modal__step-description {
  @include font-size(12px);
  @include line-height(16px);
  color: var(--fg-secondary);
  margin: 0;
}

.import-modal__progress {
  display: flex;
  align-items: center;
  gap: $base-space * 2;
  padding: $base-space * 2 $base-space * 4;
  border-bottom: 1px solid var(--border-color);
}

.import-modal__progress-bar {
  flex: 1;
  height: $base-space;
  background: var(--bg-tertiary);
  border-radius: $border-radius-s;
  overflow: hidden;
}

.import-modal__progress-fill {
  height: 100%;
  background: var(--primary-color);
  border-radius: $border-radius-s;
  transition: $swift-ease-out;
}

.import-modal__progress-text {
  @include font-size(14px);
  @include line-height(18px);
  color: var(--fg-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.import-modal__content {
  flex: 1;
  overflow-y: auto;
  padding: $base-space * 4;
  min-height: 400px;
}

.import-modal__step-content-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.import-modal__navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $base-space * 3 $base-space * 4;
  border-top: 1px solid var(--border-color);
  background: var(--bg-secondary);
}

.import-modal__navigation-right {
  display: flex;
  gap: $base-space * 2;
  align-items: center;
}

.import-modal__error {
  display: flex;
  align-items: flex-start;
  gap: $base-space + 2px;
  padding: $base-space * 2 $base-space * 4;
  background: var(--error-bg);
  border-top: 1px solid var(--error-color);
}

.import-modal__error-icon {
  color: var(--error-color);
  font-size: 1.2rem;
  margin-top: calc($base-space / 4);
  flex-shrink: 0;
}

.import-modal__error-content {
  flex: 1;

  h4 {
    @include font-size(16px);
    @include line-height(24px);
    margin: 0 0 $base-space 0;
    color: var(--error-color);
    font-weight: 600;
  }

  p {
    @include font-size(14px);
    @include line-height(18px);
    margin: 0 0 $base-space + 2px 0;
    color: var(--fg-primary);
  }
}

// Responsive design
@include media("<desktop") {
  .import-modal {
    width: 95vw !important;
    max-height: 95vh !important;
  }

  .import-modal__steps {
    flex-direction: column;
    gap: $base-space * 2;
    align-items: flex-start;
  }

  .import-modal__step {
    min-width: auto;
    width: 100%;
  }

  .import-modal__navigation {
    flex-direction: column;
    gap: $base-space * 2;
    align-items: stretch;
  }

  .import-modal__navigation-right {
    justify-content: center;
  }
}

.import-modal__button-spinner {
  margin-right: $base-space;
}

// Note: CSS variables are defined globally in the theme system</style>