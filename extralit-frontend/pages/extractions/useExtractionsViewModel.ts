import { computed, ref, shallowRef, watch } from "vue";
import { useResolve } from "ts-injecty";
import { GetWorkspaceProjectionUseCase } from "~/v2/domain/usecases/get-workspace-projection-use-case";
import { type WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { buildAnnotationUrl, ANNOTATION_CELL_LINKS_ENABLED } from "~/v2/domain/entities/projection/grid-adapter";
// Documented v1 exception: workspace selection survives Phase 6 (see plan Global Constraints).
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

export const useExtractionsViewModel = (workspaceIdOverride?: string | null) => {
  const getWorkspaceProjectionUseCase = useResolve(GetWorkspaceProjectionUseCase);
  const workspacesStore = useWorkspaces();

  // shallowRef: preserves the exact WorkspaceProjection instance the use-case returns
  // (avoids Vue wrapping it in a reactive Proxy) — the grid's `bandParity`/`toPerspectiveData`
  // adapters and view-model identity assertions both rely on referential equality.
  const projection = shallowRef<WorkspaceProjection | null>(null);
  const isLoading = ref(false);
  const loadFailed = ref(false);

  const workspaceId = computed(() => workspaceIdOverride ?? workspacesStore.get().selectedWorkspace?.id ?? null);

  const load = async () => {
    if (!workspaceId.value) return;
    isLoading.value = true;
    loadFailed.value = false;
    try {
      projection.value = await getWorkspaceProjectionUseCase.execute(workspaceId.value);
    } catch {
      loadFailed.value = true; // AxiosErrorHandler already notified
    } finally {
      isLoading.value = false;
    }
  };

  watch(workspaceId, load);

  const onCellClick = ({ schemaId, reference }: { schemaId: string; reference: string }): string => {
    const url = buildAnnotationUrl(schemaId, reference);
    if (ANNOTATION_CELL_LINKS_ENABLED) {
      // Guarded off: annotation-mode cannot resolve v2 schema ids yet (see grid-adapter.ts).
      window.location.href = url;
    }
    return url;
  };

  return { projection, isLoading, loadFailed, workspaceId, load, onCellClick };
};
