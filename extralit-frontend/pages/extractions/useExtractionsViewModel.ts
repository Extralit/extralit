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

  // Race-safety: `load()` can be re-entered concurrently — e.g. `ensureWorkspaces()` flips
  // `workspaceId` from null to a real id mid-flight, firing `watch(workspaceId, load)` before
  // the page's own `await load()` continuation resumes, or the user switches workspace while a
  // load is still in flight. `requestToken` lets a stale in-flight call detect it has been
  // superseded before it writes to shared state; `inFlight` dedupes concurrent calls for the
  // same workspace id into a single `execute()` call.
  let requestToken = 0;
  let inFlight: { workspaceId: string; token: number; promise: Promise<void> } | null = null;

  const load = (): Promise<void> => {
    const id = workspaceId.value;
    if (!id) return Promise.resolve();

    if (inFlight && inFlight.workspaceId === id) {
      return inFlight.promise;
    }

    const token = ++requestToken;
    isLoading.value = true;
    loadFailed.value = false;

    const promise = (async () => {
      try {
        const result = await getWorkspaceProjectionUseCase.execute(id);
        if (token !== requestToken) return; // superseded by a newer load
        projection.value = result;
      } catch {
        if (token !== requestToken) return; // superseded by a newer load
        loadFailed.value = true; // AxiosErrorHandler already notified
      } finally {
        if (token === requestToken) {
          isLoading.value = false;
        }
        // Only the call that created the current `inFlight` entry may clear it — a stale
        // ping-pong (w-1 -> w-2 -> w-1) can share `workspaceId` with a newer generation's
        // entry, so identity is keyed on `token`, not the string id.
        if (inFlight?.token === token) {
          inFlight = null;
        }
      }
    })();

    inFlight = { workspaceId: id, token, promise };
    return promise;
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

  // Wired to `ExtractionsGrid`'s `load-error` emit (see its doc comment): a rejection while
  // building/loading the Perspective table for the current projection is surfaced through
  // this same `loadFailed` flag the page already renders `extractions.loadError` for, so the
  // user is never left staring at a blank, unexplained grid.
  const onGridLoadError = (): void => {
    loadFailed.value = true;
  };

  return { projection, isLoading, loadFailed, workspaceId, load, onCellClick, onGridLoadError };
};
