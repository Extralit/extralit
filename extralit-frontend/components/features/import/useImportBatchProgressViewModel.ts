/**
 * View model for ImportBatchProgress component
 * Handles sequential batch upload logic with job status polling
 */

import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { useResolve } from "ts-injecty";
import type { ImportResultSummary } from "./types";
import type { DocumentMetadata } from "~/v1/domain/entities/import/ImportAnalysis";
import { BulkUploadDocumentsUseCase } from "~/v1/domain/usecases/bulk-upload-documents-use-case";
import { GetJobStatusUseCase, type JobStatus } from "~/v1/domain/usecases/get-job-status-use-case";
import { CreateImportHistoryUseCase } from "~/v1/domain/usecases/create-import-history-use-case";
import { TableData } from "~/v1/domain/entities/table/TableData";

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

export const useImportBatchProgressViewModel = (
  props: {
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
    dataframeData?: TableData;
    bibFileName?: string;
    pdfFiles?: File[];
  },
  emit?: (event: string, data?: any) => void
) => {
  const bulkUploadUseCase = useResolve(BulkUploadDocumentsUseCase);
  const jobStatusUseCase = useResolve(GetJobStatusUseCase);
  const createImportHistoryUseCase = useResolve(CreateImportHistoryUseCase);

  // Reactive state
  const isUploading = ref(false);
  const isCompleted = ref(false);
  const isCancelled = ref(false);
  const isCancelling = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");

  // Import history tracking
  const importHistoryId = ref<string | null>(null);

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
      return currentBatch.references.filter((ref) => {
        const jobId = allJobIds.value[ref];
        return jobId && (jobStatuses.value[jobId] === "finished" || jobStatuses.value[jobId] === "failed");
      }).length;
    }
    return 0;
  });

  const overallProgressPercentage = computed(() => {
    if (totalReferences.value === 0) return 0;
    return Math.round((completedReferences.value / totalReferences.value) * 100);
  });

  const batchProgressPercentage = computed(() => {
    if (currentBatchSize.value === 0) return 0;
    return Math.round((completedInCurrentBatch.value / currentBatchSize.value) * 100);
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

  // Helper functions (defined first to avoid dependency issues)
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

  const stopStatusPolling = () => {
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value);
      statusPollingInterval.value = null;
    }
  };

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
    importHistoryId.value = null; // Reset import history ID
    stopStatusPolling();
  };

  const createBatchesInternal = () => {
    totalReferences.value = Object.keys(props.uploadData.confirmedDocuments).length;
    batches.value = createBatches(props.uploadData.confirmedDocuments, batchSize.value);
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

  const startStatusPolling = () => {
    if (statusPollingInterval.value) {
      return; // Already polling
    }

    statusPollingInterval.value = setInterval(async () => {
      await pollJobStatusesInternal();
    }, pollingIntervalMs.value);
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
        (status) => status === "finished" || status === "failed"
      ).length;
    } catch (error) {
      console.error("Error polling job statuses:", error);
    }
  };

  const uploadBatchInternal = async (batch: BatchInfo) => {
    const response = await uploadBatch(batch, props.uploadData.confirmedDocuments, props.pdfFiles || []);

    // Store job IDs globally
    Object.assign(allJobIds.value, response.job_ids);

    // Initialize job statuses
    Object.values(response.job_ids).forEach((jobId: string) => {
      jobStatuses.value[jobId] = "queued";
    });

    // Handle validation failures
    if (response.failed_validations.length > 0) {
      const validationErrors = handleValidationErrors(response.failed_validations);
      errors.value.push(...validationErrors);
    }

    // Start polling for this batch
    startStatusPolling();
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

  const startBatchUpload = async () => {
    isUploading.value = true;
    currentBatchIndex.value = 0;

    try {
      await processBatchSequentially();
    } catch (error) {
      handleUploadError(error);
    }
  };

  const handleUploadError = (error: any) => {
    isUploading.value = false;
    hasError.value = true;
    errorMessage.value = error.message || "An unexpected error occurred during upload";
    stopStatusPolling();
  };

  const initializeUpload = async () => {
    if (Object.keys(props.uploadData.confirmedDocuments).length === 0) {
      return;
    }

    resetState();
    createBatchesInternal();

    await createImportHistory();

    await startBatchUpload();
  };

  const createImportHistory = async () => {
    if (!props.workspace?.id || !props.bibFileName || !props.dataframeData) {
      console.warn("Cannot create import history: missing workspace ID, filename, or dataframe data");
      return;
    }

    try {
      const addReferences = Object.entries(props.uploadData.documentActions)
        .filter(([_, action]) => action === "add")
        .map(([reference]) => reference);

      // Create filtered dataframe data with only "add" references
      const filteredDataframeData = {
        schema: props.dataframeData.schema,
        data: props.dataframeData.data.filter((row: any) => {
          const possibleReferenceFields = ["reference"];
          const referenceField = possibleReferenceFields.find((field) => row[field]);

          if (!referenceField) {
            return false;
          }
          return addReferences.includes(row[referenceField]);
        }),
      };

      // Validate that we have data to send
      if (filteredDataframeData.data.length === 0) {
        console.warn("No rows with 'add' status found in dataframe data");
      }

      // Prepare metadata with document actions and associated files for all references
      const metadata: Record<string, any> = {};

      // Build metadata in the format expected by backend: {"reference": {"status": "add|update|skip|failed", "associated_files": [...]}}
      Object.entries(props.uploadData.confirmedDocuments).forEach(([reference, docMetadata]) => {
        metadata[reference] = {
          status: props.uploadData.documentActions[reference] || "add",
          associated_files: docMetadata.associated_files.map((fileInfo) =>
            typeof fileInfo === "string" ? fileInfo : fileInfo.filename
          ),
          document_create: docMetadata.document_create,
        };
      });

      metadata.summary = {
        total_documents: Object.keys(props.uploadData.confirmedDocuments).length,
        add_count: Object.values(props.uploadData.documentActions).filter((action) => action === "add").length,
        update_count: Object.values(props.uploadData.documentActions).filter((action) => action === "update").length,
        skip_count: Object.values(props.uploadData.documentActions).filter((action) => action === "skip").length,
        failed_count: 0,
      };

      const importHistoryData = {
        workspace_id: props.workspace.id,
        filename: props.bibFileName,
        data: filteredDataframeData,
        metadata,
      };

      const response = await createImportHistoryUseCase.execute(importHistoryData);

      // Store the import history ID for potential future use
      importHistoryId.value = response.id;
    } catch (error) {
      console.error("Failed to create import history:", error);

      // Provide more specific error information
      if (error instanceof Error) {
        if (error.message.includes("Dataframe data must contain a reference field")) {
          console.error("Data validation failed: missing reference field in dataframe");
        } else if (error.message.includes("workspace")) {
          console.error("Workspace validation failed");
        } else if (error.message.includes("filename")) {
          console.error("Filename validation failed");
        } else {
          console.error("Unknown error during import history creation:", error.message);
        }
      }

      // Don't fail the import if history creation fails
      // Just log the error and continue
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

  const emitProgressUpdate = () => {
    if (emit) {
      emit("progress", {
        progress: overallProgressPercentage.value,
        completedReferences: completedReferences.value,
        totalReferences: totalReferences.value,
        currentBatch: currentBatch.value,
        totalBatches: totalBatches.value,
      });
    }
  };

  const createImportSummary = (): ImportResultSummary => {
    const summary = {
      total: Object.keys(props.uploadData.confirmedDocuments).length,
      added: 0,
      updated: 0,
      skipped: 0,
      failed: failedJobs.value,
      errors: errors.value.map((e) => ({ reference: e.reference, message: e.message })),
      importId: `import_${Date.now()}`,
    };

    // Count references by their original analysis status and current job status
    Object.entries(props.uploadData.confirmedDocuments).forEach(([reference, _docMetadata]) => {
      const originalStatus = props.uploadData.documentActions[reference] || "add";
      const jobId = allJobIds.value[reference];
      const jobStatus = jobId ? jobStatuses.value[jobId] : undefined;

      // Determine final status based on job completion
      if (jobStatus === "finished") {
        // Job completed successfully - count based on original intention
        if (originalStatus === "add") {
          summary.added++;
        } else if (originalStatus === "update") {
          summary.updated++;
        }
      } else if (jobStatus === "failed") {
        // Job failed - already counted in summary.failed via failedJobs computed
        // No need to increment here as it's handled by the computed property
      } else if (originalStatus === "skip") {
        // Document was marked to skip
        summary.skipped++;
      }
      // If job is still in progress, don't count it in any completion bucket yet
    });

    return summary;
  };

  const getFailedDocuments = () => {
    const failedDocs: any[] = [];

    Object.entries(props.uploadData.confirmedDocuments).forEach(([reference, docMetadata]) => {
      const jobId = allJobIds.value[reference];
      const jobStatus = jobId ? jobStatuses.value[jobId] : undefined;

      if (jobStatus === "failed") {
        // Find the error message for this reference
        const error = errors.value.find((e) => e.reference === reference);

        failedDocs.push({
          reference,
          error: error?.message || "Unknown error occurred",
          validation_errors: error ? [error.message] : [],
        });
      }
    });

    return failedDocs;
  };

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

  // Watch for completion and emit events
  if (emit) {
    watch(
      () => isCompleted.value,
      (isCompleted) => {
        if (isCompleted) {
          const summary = createImportSummary();
          const failedDocs = getFailedDocuments();
          emit("completed", {
            importSummary: summary,
            failedDocuments: failedDocs,
            totalReferences: totalReferences.value,
            completedJobs: completedJobs.value,
            failedJobs: failedJobs.value,
            errors: errors.value,
          });
        }
      }
    );

    watch(
      () => isCancelled.value,
      (isCancelled) => {
        if (isCancelled) {
          emit("cancelled");
        }
      }
    );

    watch(
      () => hasError.value,
      (hasError) => {
        if (hasError) {
          emit("error", {
            message: errorMessage.value,
            errors: errors.value,
          });
        }
      }
    );

    // Emit progress updates
    watch(
      () => overallProgressPercentage.value,
      (progress) => {
        emit("progress", {
          progress,
          completedReferences: completedReferences.value,
          totalReferences: totalReferences.value,
          currentBatch: currentBatch.value,
          totalBatches: totalBatches.value,
        });
      }
    );
  }

  // Cleanup on unmount
  onBeforeUnmount(() => {
    stopStatusPolling();
  });

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
    importHistoryId,

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

    // Methods (only those actually used by the Vue component)
    cancelUpload,
    retryUpload,
    createImportSummary,
    getFailedDocuments,
    emitProgressUpdate,
  };
};
