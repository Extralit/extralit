/**
 * View model for ImportBatchProgress component
 * Handles sequential batch upload logic with job status polling
 */

import { ref, computed, watch, onMounted, onBeforeUnmount } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import type { ImportResultSummary } from "./types";
import type { DocumentMetadata } from "~/v1/domain/entities/import/ImportAnalysis";
import { BulkUploadDocumentsUseCase } from "~/v1/domain/usecases/bulk-upload-documents-use-case";
import { GetJobStatusUseCase, type JobStatus } from "~/v1/domain/usecases/get-job-status-use-case";
import { CreateImportHistoryUseCase } from "~/v1/domain/usecases/create-import-history-use-case";

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

export const useImportBatchProgressViewModel = (props: {
  uploadData: {
    confirmedDocuments: Record<string, DocumentMetadata>;
    documentActions: Record<string, any>;
    totalBatches: number;
    currentBatch: number;
    jobIds: Record<string, string>;
    completedJobs: number;
    failedJobs: number;
  };
  workspace?: any;
  dataframeData?: any;
  bibFileName?: string;
  pdfFiles?: File[];
}) => {
  const bulkUploadUseCase = useResolve(BulkUploadDocumentsUseCase);
  const jobStatusUseCase = useResolve(GetJobStatusUseCase);
  const importHistoryUseCase = useResolve(CreateImportHistoryUseCase);

  // Reactive state
  const isUploading = ref(false);
  const isCompleted = ref(false);
  const isCancelled = ref(false);
  const isCancelling = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");

  // Batch processing
  const batches = ref<BatchInfo[]>([]);
  const currentBatchIndex = ref(0);
  const batchSize = ref(15); // 10-20 references per batch as per requirements

  // Job tracking
  const allJobIds = ref<Record<string, string>>({}); // reference -> jobId
  const jobStatuses = ref<Record<string, JobStatus>>({});

  // Progress tracking
  const completedReferences = ref(0);
  const totalReferences = ref(0);
  const errors = ref<UploadError[]>([]);

  // Polling
  const statusPollingInterval = ref<NodeJS.Timeout | null>(null);
  const pollingIntervalMs = ref(2000); // Poll every 2 seconds

  // Computed properties
  const totalBatches = computed(() => batches.value.length);
  const currentBatch = computed(() => currentBatchIndex.value + 1);
  const currentBatchSize = computed(() => {
    if (currentBatchIndex.value < batches.value.length) {
      return batches.value[currentBatchIndex.value].references.length;
    }
    return 0;
  });
  
  const completedInCurrentBatch = computed(() => {
    if (currentBatchIndex.value < batches.value.length) {
      const currentBatch = batches.value[currentBatchIndex.value];
      return currentBatch.references.filter(ref => {
        const jobId = allJobIds.value[ref];
        return jobId && (jobStatuses.value[jobId] === 'finished' || jobStatuses.value[jobId] === 'failed');
      }).length;
    }
    return 0;
  });

  const overallProgressPercentage = computed(() => {
    return calculateOverallProgress(completedReferences.value, totalReferences.value);
  });

  const batchProgressPercentage = computed(() => {
    return calculateBatchProgress(completedInCurrentBatch.value, currentBatchSize.value);
  });

  const completedJobs = computed(() => {
    return countJobsByStatus(jobStatuses.value).completed;
  });

  const failedJobs = computed(() => {
    return countJobsByStatus(jobStatuses.value).failed;
  });

  const processingJobs = computed(() => {
    return countJobsByStatus(jobStatuses.value).processing;
  });

  const queuedJobs = computed(() => {
    return countJobsByStatus(jobStatuses.value).queued;
  });

  // Watch for upload data changes
  watch(
    () => props.uploadData,
    (newData) => {
      if (newData && Object.keys(newData.confirmedDocuments).length > 0 && !isUploading.value) {
        initializeUpload();
      }
    },
    { deep: true, immediate: true }
  );

  // Cleanup on unmount
  onBeforeUnmount(() => {
    stopStatusPolling();
  });

  // State management methods
  const resetState = () => {
    isUploading.value = false;
    isCompleted.value = false;
    isCancelled.value = false;
    isCancelling.value = false;
    hasError.value = false;
    errorMessage.value = "";
    batches.value = [];
    currentBatchIndex.value = 0;
    allJobIds.value = {};
    jobStatuses.value = {};
    completedReferences.value = 0;
    totalReferences.value = 0;
    errors.value = [];
    stopStatusPolling();
  };

  const initializeUpload = async () => {
    if (Object.keys(props.uploadData.confirmedDocuments).length === 0) {
      return;
    }

    resetState();
    createBatchesInternal();
    await startBatchUpload();
  };

  const createBatchesInternal = () => {
    totalReferences.value = Object.keys(props.uploadData.confirmedDocuments).length;
    batches.value = createBatches(props.uploadData.confirmedDocuments, batchSize.value);
  };

  const startBatchUpload = async () => {
    isUploading.value = true;
    currentBatchIndex.value = 0;

    try {
      await processBatchSequentially();
    } catch (error) {
      handleUploadError(error);
    }
  };

  const processBatchSequentially = async () => {
    for (let batchIndex = 0; batchIndex < batches.value.length; batchIndex++) {
      if (isCancelling.value) {
        isCancelled.value = true;
        isUploading.value = false;
        return;
      }

      currentBatchIndex.value = batchIndex;
      const batch = batches.value[batchIndex];

      try {
        // Upload current batch
        await uploadBatchInternal(batch);

        // Wait for all jobs in this batch to complete (success or failure)
        await waitForBatchCompletion(batch, jobStatuses.value, pollingIntervalMs.value);

        // Mark batch as completed
        batch.completed = true;

      } catch (error) {
        batch.failed = true;
        const batchErrors = handleBatchError(batch, error);
        errors.value.push(...batchErrors);
      }
    }

    // All batches completed - set completed state
    stopStatusPolling();
    isUploading.value = false;
    isCompleted.value = true;
  };

  const uploadBatchInternal = async (batch: BatchInfo) => {
    const response = await uploadBatch(
      batch,
      props.uploadData.confirmedDocuments,
      props.pdfFiles || []
    );

    // Store job IDs globally
    Object.assign(allJobIds.value, response.job_ids);

    // Initialize job statuses
    Object.values(response.job_ids).forEach((jobId: string) => {
      jobStatuses.value[jobId] = 'queued';
    });

    // Handle validation failures
    if (response.failed_validations.length > 0) {
      const validationErrors = handleValidationErrors(response.failed_validations);
      errors.value.push(...validationErrors);
    }

    // Start polling for this batch
    startStatusPolling();
  };

  const startStatusPolling = () => {
    if (statusPollingInterval.value) {
      return; // Already polling
    }

    statusPollingInterval.value = setInterval(async () => {
      await pollJobStatusesInternal();
    }, pollingIntervalMs.value);
  };

  const stopStatusPolling = () => {
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value);
      statusPollingInterval.value = null;
    }
  };

  const pollJobStatusesInternal = async () => {
    if (Object.keys(allJobIds.value).length === 0) {
      return;
    }

    try {
      const jobIds = Object.values(allJobIds.value);
      const newJobStatuses = await pollJobStatuses(jobIds);

      // Update job statuses
      Object.assign(jobStatuses.value, newJobStatuses);

      // Update completed references count
      completedReferences.value = Object.values(jobStatuses.value).filter(
        status => status === 'finished' || status === 'failed'
      ).length;

    } catch (error) {
      console.error("Error polling job statuses:", error);
    }
  };

  const createFinalImportSummary = async () => {
    try {
      // Create import history record with metadata
      const metadata = createImportMetadata();
      await createImportHistory(
        props.workspace,
        props.bibFileName || "",
        createFilteredDataframeData(),
        metadata
      );

      // Create and return summary data
      const importSummary = createImportSummary(
        props.uploadData.confirmedDocuments,
        props.uploadData.documentActions,
        allJobIds.value,
        jobStatuses.value,
        errors.value
      );

      return importSummary;

    } catch (error) {
      console.error("Error creating final import summary:", error);
      handleUploadError(error);
      throw error;
    }
  };

  const cancelUpload = async () => {
    if (isCancelling.value) return;

    isCancelling.value = true;
    stopStatusPolling();

    // Note: We can't actually cancel running jobs, but we can stop processing new batches
    // The jobs will continue to run in the background

    setTimeout(() => {
      isCancelled.value = true;
      isUploading.value = false;
      isCancelling.value = false;
    }, 1000);
  };

  const retryUpload = async () => {
    hasError.value = false;
    errorMessage.value = "";
    await initializeUpload();
  };

  const handleUploadError = (error: any) => {
    isUploading.value = false;
    hasError.value = true;
    errorMessage.value = error.message || "An unexpected error occurred during upload";
    stopStatusPolling();
  };

  const createImportMetadata = () => {
    const metadata: Record<string, any> = {};

    // Create metadata for each reference with status and associated files
    // Only include references that were actually uploaded (add or update status with PDFs)
    Object.entries(props.uploadData.confirmedDocuments).forEach(([reference, docMetadata]) => {
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
  };

  const createFilteredDataframeData = () => {
    if (!props.dataframeData || !props.dataframeData.data) {
      return null;
    }

    // Filter dataframe data to only include references that were actually uploaded
    const uploadedReferences = new Set(Object.keys(props.uploadData.confirmedDocuments));

    const filteredData = props.dataframeData.data.filter((row: Record<string, any>) => {
      const reference = row.reference || row.key;
      return uploadedReferences.has(reference);
    });

    return {
      ...props.dataframeData,
      data: filteredData,
    };
  };

  const reset = () => {
    resetState();
  };

  // Helper functions
  const createBatches = (confirmedDocuments: Record<string, DocumentMetadata>, batchSize = 15): BatchInfo[] => {
    const references = Object.keys(confirmedDocuments);
    const batchArray: BatchInfo[] = [];

    for (let i = 0; i < references.length; i += batchSize) {
      const batchReferences = references.slice(i, i + batchSize);
      batchArray.push({
        batchIndex: Math.floor(i / batchSize),
        references: batchReferences,
        jobIds: {},
        completed: false,
        failed: false,
      });
    }

    return batchArray;
  };

  const uploadBatch = async (
    batch: BatchInfo,
    confirmedDocuments: Record<string, DocumentMetadata>,
    pdfFiles: File[]
  ) => {
    // Prepare documents for this batch
    const batchDocuments: Record<string, DocumentMetadata> = {};
    const batchFiles: File[] = [];
    const addedFiles = new Set<string>(); // Track files to avoid duplicates

    for (const reference of batch.references) {
      const docMetadata = confirmedDocuments[reference];
      if (docMetadata) {
        batchDocuments[reference] = docMetadata;

        // Find and add associated files
        for (const fileInfo of docMetadata.associated_files) {
          // Handle both FileInfo objects and string filenames
          let filename: string;
          if (typeof fileInfo === "string") {
            filename = fileInfo;
          } else if (fileInfo && typeof fileInfo === "object" && fileInfo.filename) {
            filename = fileInfo.filename;
          } else {
            continue; // Skip invalid file info
          }

          // Skip files with path prefixes (duplicates) - only use base filenames
          if (filename.includes("/")) {
            continue;
          }

          // Only add each file once to avoid duplicates
          if (!addedFiles.has(filename)) {
            const file = pdfFiles.find((f) => f.name === filename);
            if (file) {
              batchFiles.push(file);
              addedFiles.add(filename);
            }
          }
        }
      }
    }

    // Send bulk upload request for this batch
    const response = await bulkUploadUseCase.execute(batchDocuments, batchFiles);

    // Store job IDs for this batch
    batch.jobIds = response.job_ids;

    return response;
  };

  const pollJobStatuses = async (jobIds: string[]): Promise<Record<string, JobStatus>> => {
    if (jobIds.length === 0) {
      return {};
    }

    const statusMap = await jobStatusUseCase.executeMultiple(jobIds);
    const statusResults: Record<string, JobStatus> = {};

    Object.values(statusMap).forEach((jobResponse: any) => {
      statusResults[jobResponse.id] = jobResponse.status;
    });

    return statusResults;
  };

  const waitForBatchCompletion = (
    batch: BatchInfo,
    jobStatuses: Record<string, JobStatus>,
    pollingIntervalMs = 2000
  ): Promise<void> => {
    const jobIds = Object.values(batch.jobIds);

    return new Promise<void>((resolve) => {
      const checkCompletion = () => {
        const allCompleted = jobIds.every((jobId) => {
          const status = jobStatuses[jobId];
          return status === "finished" || status === "failed";
        });

        if (allCompleted) {
          resolve();
        } else {
          // Continue polling
          setTimeout(checkCompletion, pollingIntervalMs);
        }
      };

      checkCompletion();
    });
  };

  const createImportHistory = async (
    workspace: any,
    bibFileName: string,
    dataframeData: any,
    metadata?: Record<string, any>
  ) => {
    if (!dataframeData || !workspace) {
      return null;
    }

    return await importHistoryUseCase.execute({
      workspace_id: workspace.id,
      filename: bibFileName || "import.bib",
      data: dataframeData,
      metadata,
    });
  };

  /**
   * Creates import result summary with accurate counts
   * @param confirmedDocuments - Documents that were selected for upload
   * @param documentActions - Original analysis status for each reference
   * @param allJobIds - Mapping of reference to job ID
   * @param jobStatuses - Current job statuses by job ID
   * @param errors - Upload errors
   */
  const createImportSummary = (
    confirmedDocuments: Record<string, DocumentMetadata>,
    documentActions: Record<string, "add" | "update" | "skip" | "ignore" | "failed">,
    allJobIds: Record<string, string>,
    jobStatuses: Record<string, JobStatus>,
    errors: UploadError[]
  ): ImportResultSummary => {
    const summary = {
      total: 0,
      added: 0,
      updated: 0,
      skipped: 0,
      failed: 0,
      errors: errors.map((e) => ({ reference: e.reference, message: e.message })),
      importId: `import_${Date.now()}`,
    };

    // Count references by their original analysis status and current job status
    Object.entries(confirmedDocuments).forEach(([reference, _docMetadata]) => {
      const originalStatus = documentActions[reference] || "add";
      const jobId = allJobIds[reference];
      const jobStatus = jobId ? jobStatuses[jobId] : undefined;

      summary.total++;

      // Determine final status based on job completion
      if (jobStatus === "finished") {
        // Job completed successfully - count based on original intention
        if (originalStatus === "add") {
          summary.added++;
        } else if (originalStatus === "update") {
          summary.updated++;
        }
      } else if (jobStatus === "failed") {
        // Job failed
        summary.failed++;
      } else if (originalStatus === "skip") {
        // Document was marked to skip (though these shouldn't be in confirmedDocuments)
        summary.skipped++;
      }
      // If job is still in progress, don't count it in any completion bucket yet
    });

    return summary;
  };

  // Progress calculation helpers
  const calculateOverallProgress = (completedReferences: number, totalReferences: number): number => {
    if (totalReferences === 0) return 0;
    return Math.round((completedReferences / totalReferences) * 100);
  };

  const calculateBatchProgress = (completedInBatch: number, batchSize: number): number => {
    if (batchSize === 0) return 0;
    return Math.round((completedInBatch / batchSize) * 100);
  };

  // Job status counting helpers
  const countJobsByStatus = (jobStatuses: Record<string, JobStatus>) => {
    const statusCounts = {
      completed: 0,
      failed: 0,
      processing: 0,
      queued: 0,
    };

    Object.values(jobStatuses).forEach((status) => {
      switch (status) {
        case "finished":
          statusCounts.completed++;
          break;
        case "failed":
          statusCounts.failed++;
          break;
        case "started":
          statusCounts.processing++;
          break;
        case "queued":
        case "deferred":
          statusCounts.queued++;
          break;
      }
    });

    return statusCounts;
  };

  // Error handling helpers
  const handleBatchError = (batch: BatchInfo, error: any): UploadError[] => {
    return batch.references.map((reference) => ({
      reference,
      message: error.message || "Batch upload failed",
    }));
  };

  const handleValidationErrors = (validationErrors: string[]): UploadError[] => {
    return validationErrors.map((error) => ({
      reference: "validation",
      message: error,
    }));
  };

  return {
    // Reactive state
    isUploading,
    isCompleted,
    isCancelled,
    isCancelling,
    hasError,
    errorMessage,
    batches,
    currentBatchIndex,
    batchSize,
    allJobIds,
    jobStatuses,
    completedReferences,
    totalReferences,
    errors,
    statusPollingInterval,
    pollingIntervalMs,

    // Computed properties
    totalBatches,
    currentBatch,
    currentBatchSize,
    completedInCurrentBatch,
    overallProgressPercentage,
    batchProgressPercentage,
    completedJobs,
    failedJobs,
    processingJobs,
    queuedJobs,

    // Methods
    initializeUpload,
    resetState,
    createBatchesInternal,
    startBatchUpload,
    processBatchSequentially,
    uploadBatchInternal,
    startStatusPolling,
    stopStatusPolling,
    pollJobStatusesInternal,
    createFinalImportSummary,
    cancelUpload,
    retryUpload,
    handleUploadError,
    createImportMetadata,
    createFilteredDataframeData,
    reset,

    // Helper functions (for compatibility)
    createBatches,
    uploadBatch,
    pollJobStatuses,
    waitForBatchCompletion,
    createImportHistory,
    createImportSummary,
    calculateOverallProgress,
    calculateBatchProgress,
    countJobsByStatus,
    handleBatchError,
    handleValidationErrors,
  };
};
