/**
 * Use case for polling job status
 */

import type { AxiosInstance } from "axios";

// Job status from backend (maps to RQ JobStatus)
export type JobStatus = "queued" | "started" | "finished" | "failed" | "deferred" | "canceled";

export interface JobResponse {
  id: string;
  status: JobStatus;
}

export class GetJobStatusUseCase {
  constructor(private readonly axios: AxiosInstance) {}

  async execute(jobId: string): Promise<JobResponse> {
    const response = await this.axios.get<JobResponse>(`/v1/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Poll multiple job statuses in batches to avoid overwhelming the connection pool
   */
  async executeMultiple(jobIds: string[], batchSize = 5): Promise<Record<string, JobResponse>> {
    const statusMap: Record<string, JobResponse> = {};

    // Process job IDs in batches
    for (let i = 0; i < jobIds.length; i += batchSize) {
      const batch = jobIds.slice(i, i + batchSize);

      const batchPromises = batch.map(async (jobId) => {
        try {
          const result = await this.execute(jobId);
          return { jobId, result };
        } catch (error) {
          // Return failed status for jobs that can't be fetched
          return {
            jobId,
            result: {
              id: jobId,
              status: "failed" as JobStatus,
            },
          };
        }
      });

      const batchResults = await Promise.all(batchPromises);

      // Add batch results to status map
      batchResults.forEach(({ jobId, result }) => {
        statusMap[jobId] = result;
      });

      // Add a small delay between batches to reduce connection pressure
      if (i + batchSize < jobIds.length) {
        await new Promise((resolve) => setTimeout(resolve, 100));
      }
    }

    return statusMap;
  }
}
