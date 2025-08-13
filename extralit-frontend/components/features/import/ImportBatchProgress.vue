<template>
  <div class="import-batch-progress">
    <!-- Upload in progress -->
    <div v-if="isUploading" class="upload-container">
      <!-- Overall progress header -->
      <div class="progress-header">
        <h3>Importing Documents</h3>
        <p class="progress-subtitle">
          Processing {{ totalReferences }} references in {{ totalBatches }} batches
        </p>
      </div>

      <!-- Overall progress bar -->
      <div class="overall-progress">
        <div class="progress-info">
          <span class="progress-label">Overall Progress</span>
          <span class="progress-percentage">{{ overallProgressPercentage }}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: overallProgressPercentage + '%' }"></div>
        </div>
        <div class="progress-stats">
          <span>{{ completedReferences }} of {{ totalReferences }} references completed</span>
        </div>
      </div>

      <!-- Current batch info -->
      <div class="batch-info">
        <h4>Current Batch: {{ currentBatch }} of {{ totalBatches }}</h4>
        <div class="batch-progress">
          <div class="progress-info">
            <span class="progress-label">Batch Progress</span>
            <span class="progress-percentage">{{ batchProgressPercentage }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill batch-fill" :style="{ width: batchProgressPercentage + '%' }"></div>
          </div>
          <div class="progress-stats">
            <span>{{ completedInCurrentBatch }} of {{ currentBatchSize }} references in current batch</span>
          </div>
        </div>
      </div>

      <!-- Job status details -->
      <div class="job-details">
        <div class="job-stats">
          <div class="stat-item stat-completed">
            <span class="stat-label">Completed:</span>
            <span class="stat-value">{{ completedJobs }}</span>
          </div>
          <div class="stat-item stat-processing">
            <span class="stat-label">Processing:</span>
            <span class="stat-value">{{ processingJobs }}</span>
          </div>
          <div class="stat-item stat-queued">
            <span class="stat-label">Queued:</span>
            <span class="stat-value">{{ queuedJobs }}</span>
          </div>
          <div class="stat-item stat-failed">
            <span class="stat-label">Failed:</span>
            <span class="stat-value">{{ failedJobs }}</span>
          </div>
        </div>

        <!-- Error details -->
        <div v-if="errors.length > 0" class="error-section">
          <h5>Upload Errors</h5>
          <div class="error-list">
            <div v-for="error in errors" :key="error.reference" class="error-item">
              <strong>{{ error.reference }}:</strong> {{ error.message }}
            </div>
          </div>
        </div>
      </div>

      <!-- Cancel button -->
      <div class="upload-actions">
        <BaseButton variant="outline" @click="cancelUpload" :disabled="isCancelling">
          {{ isCancelling ? 'Cancelling...' : 'Cancel Upload' }}
        </BaseButton>
      </div>
    </div>

    <!-- Upload completed -->
    <div v-else-if="isCompleted" class="completion-container">
      <div class="completion-header">
        <BaseIcon icon-name="check" class="completion-icon" />
        <h3>Import Completed</h3>
        <p>All batches have been processed successfully</p>
      </div>

      <div class="completion-stats">
        <div class="stat-item stat-completed">
          <span class="stat-label">Successfully Imported:</span>
          <span class="stat-value">{{ completedJobs }}</span>
        </div>
        <div v-if="failedJobs > 0" class="stat-item stat-failed">
          <span class="stat-label">Failed:</span>
          <span class="stat-value">{{ failedJobs }}</span>
        </div>
      </div>

      <!-- Show errors if any -->
      <div v-if="errors.length > 0" class="error-section">
        <h5>Import Errors</h5>
        <div class="error-list">
          <div v-for="error in errors" :key="error.reference" class="error-item">
            <strong>{{ error.reference }}:</strong> {{ error.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- Upload cancelled -->
    <div v-else-if="isCancelled" class="cancellation-container">
      <div class="cancellation-header">
        <BaseIcon icon-name="close" class="cancellation-icon" />
        <h3>Import Cancelled</h3>
        <p>The import process was cancelled by user</p>
      </div>

      <div class="cancellation-stats">
        <div class="stat-item">
          <span class="stat-label">Completed before cancellation:</span>
          <span class="stat-value">{{ completedJobs }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Cancelled:</span>
          <span class="stat-value">{{ totalReferences - completedJobs }}</span>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="hasError" class="error-container">
      <div class="error-header">
        <BaseIcon icon-name="danger" class="error-icon" />
        <h3>Import Failed</h3>
        <p>{{ errorMessage }}</p>
      </div>

      <div class="error-actions">
        <BaseButton variant="outline" @click="retryUpload">
          Retry Upload
        </BaseButton>
      </div>
    </div>

    <!-- Initial state -->
    <div v-else class="initial-container">
      <div class="initial-message">
        <h3>Ready to Import</h3>
        <p>Click "Start Import" to begin the batch upload process</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import "assets/icons/check";
import "assets/icons/close";
import "assets/icons/danger";
import type { DocumentMetadata } from "~/v1/domain/entities/import/ImportAnalysis";
import type { ImportUploadData } from "./types";
import type { JobStatus } from "~/v1/domain/usecases/get-job-status-use-case";
import { useImportBatchProgressViewModel } from "./useImportBatchProgressViewModel";

interface BatchInfo {
  batchIndex: number;
  references: string[];
  jobIds: Record<string, string>;
  completed: boolean;
  failed: boolean;
}

interface UploadError {
  reference: string;
  message: string;
}

export default {
  name: "ImportBatchProgress",

  props: {
    uploadData: {
      type: Object as () => ImportUploadData,
      default: () => ({
        confirmedDocuments: {},
        documentActions: {},
        totalBatches: 0,
        currentBatch: 0,
        jobIds: {},
        completedJobs: 0,
        failedJobs: 0,
      }),
    },
    workspace: {
      type: Object,
      default: null,
    },
    dataframeData: {
      type: Object,
      default: null,
    },
    bibFileName: {
      type: String,
      default: "",
    },
    pdfFiles: {
      type: Array as () => File[],
      default: () => [],
    },
  },

  emits: ["completed", "cancelled", "error", "progress"],

  data() {
    return {
      // Upload state
      isUploading: false,
      isCompleted: false,
      isCancelled: false,
      isCancelling: false,
      hasError: false,
      errorMessage: "",

      // Batch processing
      batches: [] as BatchInfo[],
      currentBatchIndex: 0,
      batchSize: 15, // 10-20 references per batch as per requirements

      // Job tracking
      allJobIds: {} as Record<string, string>, // reference -> jobId
      jobStatuses: {} as Record<string, JobStatus>,

      // Progress tracking
      completedReferences: 0,
      totalReferences: 0,
      errors: [] as UploadError[],

      // Polling
      statusPollingInterval: null as NodeJS.Timeout | null,
      pollingIntervalMs: 2000, // Poll every 2 seconds
    };
  },

  computed: {
    totalBatches() {
      return this.batches.length;
    },

    currentBatch() {
      return this.currentBatchIndex + 1;
    },

    currentBatchSize() {
      if (this.currentBatchIndex < this.batches.length) {
        return this.batches[this.currentBatchIndex].references.length;
      }
      return 0;
    },

    completedInCurrentBatch() {
      if (this.currentBatchIndex < this.batches.length) {
        const currentBatch = this.batches[this.currentBatchIndex];
        return currentBatch.references.filter(ref => {
          const jobId = this.allJobIds[ref];
          return jobId && (this.jobStatuses[jobId] === 'finished' || this.jobStatuses[jobId] === 'failed');
        }).length;
      }
      return 0;
    },

    overallProgressPercentage() {
      return this.viewModel.calculateOverallProgress(this.completedReferences, this.totalReferences);
    },

    batchProgressPercentage() {
      return this.viewModel.calculateBatchProgress(this.completedInCurrentBatch, this.currentBatchSize);
    },

    completedJobs() {
      return this.viewModel.countJobsByStatus(this.jobStatuses).completed;
    },

    failedJobs() {
      return this.viewModel.countJobsByStatus(this.jobStatuses).failed;
    },

    processingJobs() {
      return this.viewModel.countJobsByStatus(this.jobStatuses).processing;
    },

    queuedJobs() {
      return this.viewModel.countJobsByStatus(this.jobStatuses).queued;
    },
  },

  watch: {
    uploadData: {
      handler(newData: ImportUploadData) {
        if (newData && Object.keys(newData.confirmedDocuments).length > 0 && !this.isUploading) {
          this.initializeUpload();
        }
      },
      deep: true,
      immediate: true,
    },
  },

  beforeUnmount() {
    this.stopStatusPolling();
  },

  methods: {
    async initializeUpload() {
      if (Object.keys(this.uploadData.confirmedDocuments).length === 0) {
        return;
      }

      this.resetState();
      this.createBatches();
      await this.startBatchUpload();
    },

    resetState() {
      this.isUploading = false;
      this.isCompleted = false;
      this.isCancelled = false;
      this.isCancelling = false;
      this.hasError = false;
      this.errorMessage = "";
      this.batches = [];
      this.currentBatchIndex = 0;
      this.allJobIds = {};
      this.jobStatuses = {};
      this.completedReferences = 0;
      this.totalReferences = 0;
      this.errors = [];
      this.stopStatusPolling();
    },

    createBatches() {
      this.totalReferences = Object.keys(this.uploadData.confirmedDocuments).length;
      this.batches = this.viewModel.createBatches(this.uploadData.confirmedDocuments, this.batchSize);
    },

    async startBatchUpload() {
      this.isUploading = true;
      this.currentBatchIndex = 0;

      try {
        await this.processBatchSequentially();
      } catch (error) {
        this.handleUploadError(error);
      }
    },

    async processBatchSequentially() {
      for (let batchIndex = 0; batchIndex < this.batches.length; batchIndex++) {
        if (this.isCancelling) {
          this.isCancelled = true;
          this.isUploading = false;
          this.$emit("cancelled");
          return;
        }

        this.currentBatchIndex = batchIndex;
        const batch = this.batches[batchIndex];

        try {
          // Upload current batch
          await this.uploadBatch(batch);

          // Wait for all jobs in this batch to complete (success or failure)
          await this.waitForBatchCompletion(batch);

          // Mark batch as completed
          batch.completed = true;

        } catch (error) {
          batch.failed = true;
          this.handleBatchError(batch, error);
        }
      }

      // All batches completed
      await this.finalizeBatchUpload();
    },

    async uploadBatch(batch: BatchInfo) {
      const response = await this.viewModel.uploadBatch(
        batch,
        this.uploadData.confirmedDocuments,
        this.pdfFiles
      );

      // Store job IDs globally
      Object.assign(this.allJobIds, response.job_ids);

      // Initialize job statuses
      Object.values(response.job_ids).forEach((jobId: string) => {
        this.jobStatuses[jobId] = 'queued';
      });

      // Handle validation failures
      if (response.failed_validations.length > 0) {
        const validationErrors = this.viewModel.handleValidationErrors(response.failed_validations);
        this.errors.push(...validationErrors);
      }

      // Start polling for this batch
      this.startStatusPolling();
    },

    async waitForBatchCompletion(batch: BatchInfo) {
      return await this.viewModel.waitForBatchCompletion(
        batch,
        this.jobStatuses,
        this.pollingIntervalMs
      );
    },

    startStatusPolling() {
      if (this.statusPollingInterval) {
        return; // Already polling
      }

      this.statusPollingInterval = setInterval(async () => {
        await this.pollJobStatuses();
      }, this.pollingIntervalMs);
    },

    stopStatusPolling() {
      if (this.statusPollingInterval) {
        clearInterval(this.statusPollingInterval);
        this.statusPollingInterval = null;
      }
    },

    async pollJobStatuses() {
      if (Object.keys(this.allJobIds).length === 0) {
        return;
      }

      try {
        const jobIds = Object.values(this.allJobIds);
        const newJobStatuses = await this.viewModel.pollJobStatuses(jobIds);

        // Update job statuses
        Object.assign(this.jobStatuses, newJobStatuses);

        // Update completed references count
        this.completedReferences = Object.values(this.jobStatuses).filter(
          status => status === 'finished' || status === 'failed'
        ).length;

        // Emit progress update
        this.$emit("progress", {
          completedReferences: this.completedReferences,
          totalReferences: this.totalReferences,
          completedJobs: this.completedJobs,
          failedJobs: this.failedJobs,
          currentBatch: this.currentBatch,
          totalBatches: this.totalBatches,
        });

      } catch (error) {
        console.error("Error polling job statuses:", error);
      }
    },

    async finalizeBatchUpload() {
      this.stopStatusPolling();
      this.isUploading = false;
      this.isCompleted = true;

      try {
        // Create import history record with metadata
        const metadata = this.createImportMetadata();
        await this.viewModel.createImportHistory(
          this.workspace,
          this.bibFileName,
          this.createFilteredDataframeData(),
          metadata
        );

        // Create and emit normalized summary data
        const normalizedSummary = this.viewModel.createNormalizedSummary(
          this.uploadData.confirmedDocuments,
          this.uploadData.documentActions,
          this.allJobIds,
          this.jobStatuses,
          this.errors
        );

        // Convert to legacy format for backward compatibility
        const summaryData = this.viewModel.convertToLegacySummary(normalizedSummary);

        this.$emit("completed", summaryData);

      } catch (error) {
        console.error("Error finalizing import:", error);
        this.handleUploadError(error);
      }
    },

    async cancelUpload() {
      if (this.isCancelling) return;

      this.isCancelling = true;
      this.stopStatusPolling();

      // Note: We can't actually cancel running jobs, but we can stop processing new batches
      // The jobs will continue to run in the background

      setTimeout(() => {
        this.isCancelled = true;
        this.isUploading = false;
        this.isCancelling = false;
        this.$emit("cancelled");
      }, 1000);
    },

    async retryUpload() {
      this.hasError = false;
      this.errorMessage = "";
      await this.initializeUpload();
    },

    handleUploadError(error: any) {
      this.isUploading = false;
      this.hasError = true;
      this.errorMessage = error.message || "An unexpected error occurred during upload";
      this.stopStatusPolling();
      this.$emit("error", error);
    },

    handleBatchError(batch: BatchInfo, error: any) {
      const batchErrors = this.viewModel.handleBatchError(batch, error);
      this.errors.push(...batchErrors);
    },

    createImportMetadata() {
      const metadata: Record<string, any> = {};

      // Create metadata for each reference with status and associated files
      // Only include references that were actually uploaded (add or update status with PDFs)
      Object.entries(this.uploadData.confirmedDocuments).forEach(([reference, docMetadata]) => {
        const typedDocMetadata = docMetadata as DocumentMetadata;

        // Only include references that have associated files (matched PDFs)
        if (typedDocMetadata.associated_files && typedDocMetadata.associated_files.length > 0) {
          metadata[reference] = {
            status: 'add', // Default status for uploaded documents
            associated_files: typedDocMetadata.associated_files.map(fileInfo =>
              typeof fileInfo === 'string' ? fileInfo : fileInfo.filename
            ),
          };
        }
      });

      return metadata;
    },

    createFilteredDataframeData() {
      if (!this.dataframeData || !this.dataframeData.data) {
        return null;
      }

      // Filter dataframe data to only include references that were actually uploaded
      const uploadedReferences = new Set(Object.keys(this.uploadData.confirmedDocuments));

      const filteredData = this.dataframeData.data.filter((row: Record<string, any>) => {
        const reference = row.reference || row.key;
        return uploadedReferences.has(reference);
      });

      return {
        ...this.dataframeData,
        data: filteredData,
      };
    },

    reset() {
      this.resetState();
    },
  },

  setup(props) {
    const viewModel = useImportBatchProgressViewModel(props);
    return {
      viewModel,
    };
  },
};
</script>

<style lang="scss" scoped>
.import-batch-progress {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 400px;
  padding: $base-space * 3;
}

// Upload container
.upload-container {
  display: flex;
  flex-direction: column;
  gap: $base-space * 3;
  height: 100%;
}

.progress-header {
  text-align: center;

  h3 {
    margin: 0 0 $base-space 0;
    color: var(--fg-primary);
    font-size: 1.5rem;
    font-weight: 600;
  }

  .progress-subtitle {
    margin: 0;
    color: var(--fg-secondary);
    font-size: 1rem;
  }
}

// Progress bars
.overall-progress,
.batch-progress {
  .progress-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: $base-space;

    .progress-label {
      font-weight: 600;
      color: var(--fg-primary);
    }

    .progress-percentage {
      font-weight: 600;
      color: var(--bg-action);
      font-size: 1.1rem;
    }
  }

  .progress-bar {
    width: 100%;
    height: 12px;
    background: var(--bg-solid-grey-3);
    border-radius: $border-radius;
    overflow: hidden;
    margin-bottom: $base-space;

    .progress-fill {
      height: 100%;
      background: var(--color-success);
      transition: width 0.3s ease;
      border-radius: $border-radius;

      &.batch-fill {
        background: var(--bg-action);
      }
    }
  }

  .progress-stats {
    text-align: center;
    color: var(--fg-secondary);
    font-size: 0.9rem;
  }
}

// Batch info
.batch-info {
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  h4 {
    margin: 0 0 $base-space * 2 0;
    color: var(--fg-primary);
    font-size: 1.2rem;
    font-weight: 600;
  }
}

// Job details
.job-details {
  padding: $base-space * 2;
  background: var(--bg-solid-grey-2);
  border-radius: $border-radius;
  border: 1px solid var(--border-field);

  .job-stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;
    margin-bottom: $base-space * 2;

    .stat-item {
      display: flex;
      align-items: center;
      gap: $base-space;

      .stat-label {
        color: var(--fg-secondary);
        font-size: 0.9rem;
      }

      .stat-value {
        font-weight: 600;
        font-size: 1rem;
        color: var(--fg-primary);
      }

      &.stat-completed .stat-value {
        color: var(--color-success);
      }

      &.stat-processing .stat-value {
        color: var(--bg-action);
      }

      &.stat-queued .stat-value {
        color: var(--fg-secondary);
      }

      &.stat-failed .stat-value {
        color: var(--color-danger);
      }
    }
  }
}

// Error section
.error-section {
  margin-top: $base-space * 2;
  padding: $base-space * 2;
  background: var(--bg-banner-error);
  border: 1px solid var(--color-danger);
  border-radius: $border-radius;

  h5 {
    margin: 0 0 $base-space 0;
    color: var(--color-danger);
    font-weight: 600;
  }

  .error-list {
    max-height: 150px;
    overflow-y: auto;

    .error-item {
      margin-bottom: $base-space;
      font-size: 0.9rem;
      color: var(--fg-primary);

      strong {
        color: var(--color-danger);
      }
    }
  }
}

// Upload actions
.upload-actions {
  display: flex;
  justify-content: center;
  margin-top: auto;
  padding-top: $base-space * 2;
}

// Completion container
.completion-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: $base-space * 3;

  .completion-header {
    .completion-icon {
      font-size: 3rem;
      color: var(--color-success);
      margin-bottom: $base-space * 2;
    }

    h3 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
      font-size: 1.5rem;
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 1rem;
    }
  }

  .completion-stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;
    justify-content: center;

    .stat-item {
      display: flex;
      align-items: center;
      gap: $base-space;

      .stat-label {
        color: var(--fg-secondary);
        font-size: 0.9rem;
      }

      .stat-value {
        font-weight: 600;
        font-size: 1.2rem;
        color: var(--fg-primary);
      }

      &.stat-completed .stat-value {
        color: var(--color-success);
      }

      &.stat-failed .stat-value {
        color: var(--color-danger);
      }
    }
  }
}

// Cancellation container
.cancellation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: $base-space * 3;

  .cancellation-header {
    .cancellation-icon {
      font-size: 3rem;
      color: var(--fg-secondary);
      margin-bottom: $base-space * 2;
    }

    h3 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
      font-size: 1.5rem;
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 1rem;
    }
  }

  .cancellation-stats {
    display: flex;
    gap: $base-space * 3;
    flex-wrap: wrap;
    justify-content: center;

    .stat-item {
      display: flex;
      align-items: center;
      gap: $base-space;

      .stat-label {
        color: var(--fg-secondary);
        font-size: 0.9rem;
      }

      .stat-value {
        font-weight: 600;
        font-size: 1.2rem;
        color: var(--fg-primary);
      }
    }
  }
}

// Error container
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: $base-space * 3;

  .error-header {
    .error-icon {
      font-size: 3rem;
      color: var(--color-danger);
      margin-bottom: $base-space * 2;
    }

    h3 {
      margin: 0 0 $base-space 0;
      color: var(--color-danger);
      font-size: 1.5rem;
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-primary);
      font-size: 1rem;
    }
  }

  .error-actions {
    display: flex;
    justify-content: center;
  }
}

// Initial container
.initial-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;

  .initial-message {
    h3 {
      margin: 0 0 $base-space 0;
      color: var(--fg-primary);
      font-size: 1.5rem;
      font-weight: 600;
    }

    p {
      margin: 0;
      color: var(--fg-secondary);
      font-size: 1rem;
    }
  }
}
</style>
