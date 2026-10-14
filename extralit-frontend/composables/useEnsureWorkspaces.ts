import { computed } from "vue";
import { useResolve } from "ts-injecty";
import { GetWorkspacesUseCase } from "~/v1/domain/usecases/get-workspaces-use-case";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

// v2 pages are reached by direct URL (deep links from the records table, browser reload).
// Only the home page fetches workspaces, so a hard load lands with an empty store and the
// localStorage-pinned selection has nothing to restore against. Hydrate on mount here.
export const useEnsureWorkspaces = () => {
  const getWorkspacesUseCase = useResolve(GetWorkspacesUseCase);
  const workspacesStore = useWorkspaces();
  const selectedWorkspace = computed(() => workspacesStore.get().selectedWorkspace);

  const ensureWorkspaces = async () => {
    if (workspacesStore.get().workspaces.length > 0) return;
    await getWorkspacesUseCase.execute(); // saveWorkspaces + pin-restore happen inside the use-case
  };

  return { ensureWorkspaces, selectedWorkspace };
};
