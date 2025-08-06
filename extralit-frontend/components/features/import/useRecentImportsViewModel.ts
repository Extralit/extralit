/**
 * View model for RecentImports component
 * Handles reactive state management for recent imports data
 */

import { ref, computed, watch, onMounted } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { GetImportHistoryUseCase } from "~/v1/domain/usecases/get-import-history-use-case";
import type { ImportHistoryListItem } from "~/v1/domain/usecases/get-import-history-use-case";

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

  // Computed properties
  const hasWorkspace = computed(() => props.workspace && props.workspace.id);

  // Load recent imports for the current workspace
  const loadRecentImports = async () => {
    if (!hasWorkspace.value) {
      recentImports.value = [];
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response = await getImportHistoryUseCase.getRecent(props.workspace!.id, 5);
      recentImports.value = response.items;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Failed to load recent imports:", err);
      error.value = "Failed to load recent imports. Please try again.";
      recentImports.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Watch for workspace changes and reload data
  watch(
    () => props.workspace?.id,
    async (newWorkspaceId, oldWorkspaceId) => {
      // Load data when workspace changes, including from null to a value
      if (newWorkspaceId && newWorkspaceId !== oldWorkspaceId) {
        await loadRecentImports();
      }
    },
    { immediate: false }
  );

  // Load data on component mount only if workspace is available
  onMounted(async () => {
    if (hasWorkspace.value) {
      await loadRecentImports();
    }
  });

  // Retry mechanism for error recovery
  const retryLoad = async () => {
    await loadRecentImports();
  };

  return {
    // Reactive state
    recentImports,
    isLoading,
    error,

    // Computed properties
    hasWorkspace,

    // Methods
    loadRecentImports,
    retryLoad,
  };
}
