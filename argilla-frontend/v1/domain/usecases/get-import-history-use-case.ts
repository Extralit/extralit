/**
 * Use case for fetching import history records
 */

import { NuxtAxiosInstance } from "@nuxtjs/axios";

export interface ImportHistoryListItem {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  created_at: string;
  uploaded_by?: string; // User name, populated from user relationship
  total_papers: number;
  success_count: number;
  updated_count: number;
  skipped_count: number;
  failed_count: number;
}

export interface ImportHistoryListResponse {
  items: ImportHistoryListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ImportHistoryFilters {
  workspace_id?: string;
  user_id?: string;
  filename?: string;
  date_from?: string;
  date_to?: string;
}

export interface ImportHistoryListParams {
  page?: number;
  size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: ImportHistoryFilters;
}

export class GetImportHistoryUseCase {
  constructor(
    private readonly axios: NuxtAxiosInstance
  ) {}

  async execute(params: ImportHistoryListParams = {}): Promise<ImportHistoryListResponse> {
    const queryParams = new URLSearchParams();
    
    // Pagination
    if (params.page !== undefined) {
      queryParams.append('page', params.page.toString());
    }
    if (params.size !== undefined) {
      queryParams.append('size', params.size.toString());
    }
    
    // Sorting
    if (params.sort_by) {
      queryParams.append('sort_by', params.sort_by);
    }
    if (params.sort_order) {
      queryParams.append('sort_order', params.sort_order);
    }
    
    // Filters
    if (params.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          queryParams.append(key, value.toString());
        }
      });
    }

    const response = await this.axios.get<ImportHistoryListResponse>(
      `/v1/imports/history?${queryParams.toString()}`
    );

    return response.data;
  }
}