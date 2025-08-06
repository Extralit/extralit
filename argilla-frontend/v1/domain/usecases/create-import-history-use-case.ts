/**
 * Use case for creating import history records
 */

import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import type { ImportHistoryCreate } from "~/v1/domain/entities/import/ImportAnalysis";

export interface CreateImportHistoryResponse {
  id: string;
  workspace_id: string;
  filename: string;
  created_at: string;
}

export class CreateImportHistoryUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) {}

  async execute(importHistoryData: ImportHistoryCreate): Promise<CreateImportHistoryResponse> {
    const response = await this.axios.post<CreateImportHistoryResponse>("/v1/imports/history", importHistoryData);

    return response.data;
  }
}
