/**
 * View model for ImportHistoryList component
 * Handles loading, filtering, and pagination of import history
 */

import { useResolve } from "ts-injecty";
import type {
    ImportHistoryListItem,
    ImportHistoryListResponse,
    ImportHistoryFilters,
} from "~/v1/domain/usecases/get-import-history-use-case";
import {
    GetImportHistoryUseCase,
} from "~/v1/domain/usecases/get-import-history-use-case";

interface LoadHistoryParams {
    page: number;
    size: number;
    sort_by: string;
    sort_order: 'asc' | 'desc';
    filters: ImportHistoryFilters & { workspace_id?: string };
}

interface HistoryTableRow {
    id: string;
    filename: string;
    uploaded_by: string;
    created_at: string;
    total_papers: number;
    success_count: number;
    updated_count: number;
    skipped_count: number;
    failed_count: number;
    actions: string;
}

export function useImportHistoryListViewModel(props: any) {
    const getImportHistoryUseCase = useResolve(GetImportHistoryUseCase);

    // Formatting helpers
    const formatDateData = (dateString: string): string => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return {
        // Use case
        getImportHistoryUseCase,

        // Main data loading method
        async loadHistoryData(params: LoadHistoryParams): Promise<ImportHistoryListResponse> {
            return await getImportHistoryUseCase.execute(params);
        },

        // Filter helpers
        hasActiveFiltersData(filters: ImportHistoryFilters): boolean {
            return !!(
                filters.filename ||
                filters.date_from ||
                filters.date_to
            );
        },

        clearFiltersData(): ImportHistoryFilters {
            return {
                filename: "",
                date_from: "",
                date_to: "",
            };
        },

        // Pagination helpers
        calculateStartItemData(currentPage: number, pageSize: number): number {
            return (currentPage - 1) * pageSize + 1;
        },

        calculateEndItemData(currentPage: number, pageSize: number, totalItems: number): number {
            return Math.min(currentPage * pageSize, totalItems);
        },

        calculateVisiblePagesData(currentPage: number, totalPages: number, delta = 2): number[] {
            let start = Math.max(1, currentPage - delta);
            let end = Math.min(totalPages, currentPage + delta);

            // Adjust if we're near the beginning or end
            if (end - start < 2 * delta) {
                if (start === 1) {
                    end = Math.min(totalPages, start + 2 * delta);
                } else if (end === totalPages) {
                    start = Math.max(1, end - 2 * delta);
                }
            }

            const pages = [];
            for (let i = start; i <= end; i++) {
                pages.push(i);
            }
            return pages;
        },

        // Data transformation
        transformToTableDataData(items: ImportHistoryListItem[]): HistoryTableRow[] {
            return items.map((item: ImportHistoryListItem) => ({
                id: item.id,
                filename: item.filename,
                uploaded_by: item.uploaded_by || 'Unknown User',
                created_at: formatDateData(item.created_at),
                total_papers: item.total_papers,
                success_count: item.success_count,
                updated_count: item.updated_count,
                skipped_count: item.skipped_count,
                failed_count: item.failed_count,
                actions: 'view-details',
            }));
        },

        // Formatting helpers
        formatDateData,

        // Event handlers
        handleRowClickData(rowData: HistoryTableRow, emitFn: (event: string, data: any) => void, workspace: any) {
            emitFn("view-details", {
                importId: rowData.id,
                filename: rowData.filename,
                workspace: workspace,
            });
        },
    };
}