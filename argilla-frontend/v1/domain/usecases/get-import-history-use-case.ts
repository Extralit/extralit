/**
 * Use case for fetching import history records
 */

import { type NuxtAxiosInstance } from "@nuxtjs/axios";

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
  items: ImportHistoryListItem[]
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

export interface ImportHistoryListRequest {
  page?: number;
  limit?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  filters?: ImportHistoryFilters;
}

// Backend response structure
interface ImportHistoryResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  created_at: string;
  data?: any;
  metadata?: Record<string, {
    status: "add" | "update" | "skip" | "failed";
    associated_files: string[];
    error_message?: string;
    validation_errors?: string[];
    import_timestamp?: string;
  }>;
}

export class GetImportHistoryUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) { }

  async execute(params: ImportHistoryListRequest = {}): Promise<ImportHistoryListResponse> {
    const queryParams = new URLSearchParams();

    // Pagination
    if (params.page !== undefined) {
      queryParams.append("page", params.page.toString());
    }
    if (params.limit !== undefined) {
      queryParams.append("limit", params.limit.toString());
    }

    // Sorting
    if (params.sort_by) {
      queryParams.append("sort_by", params.sort_by);
    }
    if (params.sort_order) {
      queryParams.append("sort_order", params.sort_order);
    }

    // Filters
    if (params.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          queryParams.append(key, value.toString());
        }
      });
    }

    const response = await this.axios.get<ImportHistoryResponse[]>(`/v1/imports/history?${queryParams.toString()}`);

    // The API returns an array directly, not an object with items property
    const rawItems = Array.isArray(response.data) ? response.data : [];

    // Transform backend response to frontend format with calculated fields
    const items: ImportHistoryListItem[] = rawItems.map(item => {
      const counts = this.calculateCountsFromMetadata(item.metadata);

      return {
        id: item.id,
        workspace_id: item.workspace_id,
        user_id: item.user_id,
        filename: item.filename,
        created_at: item.created_at,
        uploaded_by: "Unknown User", // TODO: Get from user relationship when available
        total_papers: counts.total,
        success_count: counts.success,
        updated_count: counts.updated,
        skipped_count: counts.skipped,
        failed_count: counts.failed,
      };
    });

    return {
      items,
      total: items.length,
      page: params.page || 1,
      size: params.limit || items.length,
      pages: 1, // Since we're getting all items in one response
    };
  }

  /**
   * Calculate counts from metadata
   */
  private calculateCountsFromMetadata(metadata?: Record<string, any>): {
    total: number;
    success: number;
    updated: number;
    skipped: number;
    failed: number;
  } {
    if (!metadata) {
      return { total: 0, success: 0, updated: 0, skipped: 0, failed: 0 };
    }

    let success = 0;
    let updated = 0;
    let skipped = 0;
    let failed = 0;

    // Count statuses from metadata
    Object.values(metadata).forEach((item: any) => {
      if (item && typeof item === 'object' && item.status) {
        switch (item.status) {
          case 'add':
            success++;
            break;
          case 'update':
            updated++;
            break;
          case 'skip':
            skipped++;
            break;
          case 'failed':
            failed++;
            break;
        }
      }
    });

    const total = success + updated + skipped + failed;

    return { total, success, updated, skipped, failed };
  }

  /**
   * Fetch recent imports for sidebar display
   * @param workspaceId - The workspace ID to filter imports
   * @param limit - Maximum number of recent imports to fetch (default: 5)
   * @returns Promise<ImportHistoryListResponse> - Recent imports sorted by creation date
   */
  async getRecent(workspaceId: string, limit = 5): Promise<ImportHistoryListResponse> {
    const params: ImportHistoryListRequest = {
      limit: limit,
      sort_by: "created_at",
      sort_order: "desc",
      filters: { workspace_id: workspaceId },
    };

    return await this.execute(params);
  }
}
