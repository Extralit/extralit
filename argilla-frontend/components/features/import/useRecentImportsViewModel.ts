/**
 * View model for RecentImports component
 * Handles loading and displaying recent import history records
 */

import { ref, onMounted, watch } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import type {
  ImportHistoryListItem,
  ImportHistoryListResponse,
} from "~/v1/domain/usecases/get-import-history-use-case";
import { GetImportHistoryUseCase } from "~/v1/domain/usecases/get-import-history-use-case";

interface RecentImportsProps {
  workspace: {
    id: string;
    name: string;
  } | null;
}

export function useRecentImportsViewModel(props: RecentImportsProps) {
  const getImportHistoryUseCase = useResolve(GetImportHistoryUseCase);

  // Reactive state
  const recentImports = ref<ImportHistoryListItem[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Load recent imports for the current workspace
   */
  const loadRecentImports = async () => {
    if (!props.workspace?.id) {
      recentImports.value = [];
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response: ImportHistoryListResponse = await getImportHistoryUseCase.getRecent(
        props.workspace.id,
        5 // Limit to 5 most recent imports
      );

      recentImports.value = response.items;
    } catch (err: any) {
      console.error("Error loading recent imports:", err);
      error.value = err.message || "Failed to load recent imports";
      recentImports.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Load recent imports when component mounts
  onMounted(() => {
    loadRecentImports();
  });

  // Watch for workspace changes and reload imports
  watch(
    () => props.workspace?.id,
    (newWorkspaceId, oldWorkspaceId) => {
      if (newWorkspaceId !== oldWorkspaceId) {
        loadRecentImports();
      }
    }
  );

  return {
    // State
    recentImports,
    isLoading,
    error,

    // Methods
    loadRecentImports,
  };
}
