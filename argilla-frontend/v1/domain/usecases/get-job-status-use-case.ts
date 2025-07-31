/**
 * Use case for polling job status
 */

import { useResolve } from "ts-injecty";
import type { AxiosInstance } from "axios";

// Job status from backend (maps to RQ JobStatus)
export type JobStatus = 'queued' | 'started' | 'finished' | 'failed' | 'deferred' | 'canceled';

export interface JobResponse {
  id: string;
  status: JobStatus;
}

export class GetJobStatusUseCase {
  constructor(private readonly axios: AxiosInstance = useResolve("axios")) {}

  async execute(jobId: string): Promise<JobResponse> {
    const response = await this.axios.get<JobResponse>(`/api/v1/jobs/${jobId}`);
    return response.data;
  }

  /**
   * Poll multiple job statuses concurrently
   */
  async executeMultiple(jobIds: string[]): Promise<Record<string, JobResponse>> {
    const promises = jobIds.map(async (jobId) => {
      try {
        const result = await this.execute(jobId);
        return { jobId, result };
      } catch (error) {
        // Return failed status for jobs that can't be fetched
        return { 
          jobId, 
          result: { 
            id: jobId, 
            status: 'failed' as JobStatus 
          } 
        };
      }
    });

    const results = await Promise.all(promises);
    
    const statusMap: Record<string, JobResponse> = {};
    results.forEach(({ jobId, result }) => {
      statusMap[jobId] = result;
    });

    return statusMap;
  }
}