/**
 * View model for ImportBatchProgress component
 * Handles sequential batch upload logic with job status polling
 */

import { useResolve } from "ts-injecty";
import type { ImportSummaryData } from "./types";
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

export function useImportBatchProgressViewModel(props: any) {
  const bulkUploadUseCase = useResolve(BulkUploadDocumentsUseCase);
  const jobStatusUseCase = useResolve(GetJobStatusUseCase);
  const importHistoryUseCase = useResolve(CreateImportHistoryUseCase);

  return {
    // Use cases
    bulkUploadUseCase,
    jobStatusUseCase,
    importHistoryUseCase,

    // Batch processing methods
    createBatches(confirmedDocuments: Record<string, DocumentMetadata>, batchSize = 15): BatchInfo[] {
      const references = Object.keys(confirmedDocuments);
      const batches: BatchInfo[] = [];

      for (let i = 0; i < references.length; i += batchSize) {
        const batchReferences = references.slice(i, i + batchSize);
        batches.push({
          batchIndex: Math.floor(i / batchSize),
          references: batchReferences,
          jobIds: {},
          completed: false,
          failed: false,
        });
      }

      return batches;
    },

    async uploadBatch(batch: BatchInfo, confirmedDocuments: Record<string, DocumentMetadata>, pdfFiles: File[]) {
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
    },

    async pollJobStatuses(jobIds: string[]): Promise<Record<string, JobStatus>> {
      if (jobIds.length === 0) {
        return {};
      }

      const statusMap = await jobStatusUseCase.executeMultiple(jobIds);
      const jobStatuses: Record<string, JobStatus> = {};

      Object.values(statusMap).forEach((jobResponse: any) => {
        jobStatuses[jobResponse.id] = jobResponse.status;
      });

      return jobStatuses;
    },

    async waitForBatchCompletion(
      batch: BatchInfo,
      jobStatuses: Record<string, JobStatus>,
      pollingIntervalMs = 2000
    ): Promise<void> {
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
    },

    async createImportHistory(workspace: any, bibFileName: string, dataframeData: any, metadata?: Record<string, any>) {
      if (!dataframeData || !workspace) {
        return null;
      }

      return await importHistoryUseCase.execute({
        workspace_id: workspace.id,
        filename: bibFileName || "import.bib",
        data: dataframeData,
        metadata,
      });
    },

    createSummaryData(
      totalReferences: number,
      completedJobs: number,
      failedJobs: number,
      errors: UploadError[]
    ): ImportSummaryData {
      return {
        totalProcessed: totalReferences,
        successfullyAdded: completedJobs,
        updated: 0, // TODO: Track updates vs adds
        skipped: 0,
        failed: failedJobs,
        errors: errors.map((e) => `${e.reference}: ${e.message}`),
        importId: `import_${Date.now()}`,
      };
    },

    // Progress calculation helpers
    calculateOverallProgress(completedReferences: number, totalReferences: number): number {
      if (totalReferences === 0) return 0;
      return Math.round((completedReferences / totalReferences) * 100);
    },

    calculateBatchProgress(completedInBatch: number, batchSize: number): number {
      if (batchSize === 0) return 0;
      return Math.round((completedInBatch / batchSize) * 100);
    },

    // Job status counting helpers
    countJobsByStatus(jobStatuses: Record<string, JobStatus>) {
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
    },

    // Error handling helpers
    handleBatchError(batch: BatchInfo, error: any): UploadError[] {
      return batch.references.map((reference) => ({
        reference,
        message: error.message || "Batch upload failed",
      }));
    },

    handleValidationErrors(validationErrors: string[]): UploadError[] {
      return validationErrors.map((error) => ({
        reference: "validation",
        message: error,
      }));
    },
  };
}
