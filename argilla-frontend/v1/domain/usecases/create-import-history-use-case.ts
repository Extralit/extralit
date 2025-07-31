/**
 * Use case for creating import history records
 */

import { NuxtAxiosInstance } from "@nuxtjs/axios";
import type { ImportHistoryCreate } from "~/v1/domain/entities/import/ImportAnalysis";

export interface ImportHistoryResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  created_at: string;
}

export class CreateImportHistoryUseCase {
  constructor(
    private readonly axios: NuxtAxiosInstance
  ) {}

  async execute(importHistoryData: ImportHistoryCreate): Promise<ImportHistoryResponse> {
    const response = await this.axios.post<ImportHistoryResponse>(
      "/api/v1/imports/history",
      importHistoryData
    );

    return response.data;
  }
}