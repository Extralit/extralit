/**
 * Use case for fetching detailed import history data
 */

import { type NuxtAxiosInstance } from "@nuxtjs/axios";

export interface ImportHistoryDetailItem {
  reference: string;
  title: string;
  authors: string;
  year: string;
  journal?: string;
  doi?: string;
  pmid?: string;
  status: 'add' | 'update' | 'skip' | 'failed';
  associated_files: string[];
  error_message?: string;
  validation_errors?: string[];
  // Dynamic fields from original dataframe
  [key: string]: any;
}

export interface ImportHistoryDetailsResponse {
  id: string;
  workspace_id: string;
  user_id: string;
  filename: string;
  created_at: string;
  uploaded_by?: string;
  data: {
    schema: {
      fields: Array<{
        name: string;
        type: string;
      }>;
      primaryKey: string[];
    };
    data: Record<string, any>[];
  };
  metadata?: Record<string, any>; // Contains status and file info for each reference
  summary: {
    total_documents: number;
    add_count: number;
    update_count: number;
    skip_count: number;
    failed_count: number;
  };
}

export interface ImportHistoryDetailsFilters {
  reference?: string;
  title?: string;
  authors?: string;
  status?: string;
  error_message?: string;
}

export interface ImportHistoryDetailsParams {
  page?: number;
  size?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  filters?: ImportHistoryDetailsFilters;
}

export class GetImportHistoryDetailsUseCase {
  constructor(
    private readonly axios: NuxtAxiosInstance
  ) {}

  async execute(
    importId: string, 
    params: ImportHistoryDetailsParams = {}
  ): Promise<{
    details: ImportHistoryDetailsResponse;
    items: ImportHistoryDetailItem[];
    total: number;
    page: number;
    size: number;
    pages: number;
  }> {
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

    const response = await this.axios.get<ImportHistoryDetailsResponse>(
      `/v1/imports/history/${importId}?${queryParams.toString()}`
    );

    const details = response.data;
    
    // Process the data to create detailed items
    const items = this.processDetailItems(details);
    
    // Apply client-side pagination and filtering if needed
    const filteredItems = this.applyFilters(items, params.filters);
    const paginatedItems = this.applyPagination(filteredItems, params.page || 1, params.size || 20);
    
    return {
      details,
      items: paginatedItems.items,
      total: filteredItems.length,
      page: params.page || 1,
      size: params.size || 20,
      pages: Math.ceil(filteredItems.length / (params.size || 20)),
    };
  }

  private processDetailItems(details: ImportHistoryDetailsResponse): ImportHistoryDetailItem[] {
    const items: ImportHistoryDetailItem[] = [];
    
    // Process each data row from the dataframe
    details.data.data.forEach((row: Record<string, any>) => {
      const reference = row.reference || row.id || 'Unknown';
      const metadata = details.metadata?.[reference] || {};
      
      const item: ImportHistoryDetailItem = {
        reference,
        title: row.title || 'Unknown Title',
        authors: this.formatAuthors(row.author || row.authors),
        year: row.year?.toString() || 'Unknown',
        journal: row.journal || row.venue,
        doi: row.doi,
        pmid: row.pmid,
        status: metadata.status || 'unknown',
        associated_files: metadata.associated_files || [],
        error_message: metadata.error_message,
        validation_errors: metadata.validation_errors,
        // Include all other fields from the original data
        ...row,
      };
      
      items.push(item);
    });
    
    return items;
  }

  private formatAuthors(authors: string | string[] | undefined): string {
    if (!authors) return 'Unknown Authors';
    if (Array.isArray(authors)) {
      return authors.slice(0, 3).join(', ') + (authors.length > 3 ? ' et al.' : '');
    }
    return String(authors);
  }

  private applyFilters(
    items: ImportHistoryDetailItem[], 
    filters?: ImportHistoryDetailsFilters
  ): ImportHistoryDetailItem[] {
    if (!filters) return items;
    
    return items.filter(item => {
      if (filters.reference && !item.reference.toLowerCase().includes(filters.reference.toLowerCase())) {
        return false;
      }
      if (filters.title && !item.title.toLowerCase().includes(filters.title.toLowerCase())) {
        return false;
      }
      if (filters.authors && !item.authors.toLowerCase().includes(filters.authors.toLowerCase())) {
        return false;
      }
      if (filters.status && item.status !== filters.status) {
        return false;
      }
      if (filters.error_message && (!item.error_message || !item.error_message.toLowerCase().includes(filters.error_message.toLowerCase()))) {
        return false;
      }
      return true;
    });
  }

  private applyPagination(
    items: ImportHistoryDetailItem[], 
    page: number, 
    size: number
  ): { items: ImportHistoryDetailItem[]; total: number } {
    const startIndex = (page - 1) * size;
    const endIndex = startIndex + size;
    
    return {
      items: items.slice(startIndex, endIndex),
      total: items.length,
    };
  }
}