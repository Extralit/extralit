import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import { IWorkspaceStorage } from "@/v1/domain/services/IWorkspaceStorage";
import { useStoreFor } from "@/v1/store/create";

class WorkspaceState {
  constructor(
    public readonly workspaces: Workspace[] = [],
    public readonly selectedWorkspace: Workspace | null = null
  ) {}
}

// Utility functions for localStorage persistence
const SELECTED_WORKSPACE_KEY = "extralit-selected-workspace-id";

const loadSelectedWorkspaceId = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    return localStorage.getItem(SELECTED_WORKSPACE_KEY);
  } catch (error) {
    console.warn("Failed to load selected workspace from localStorage:", error);
    return null;
  }
};

const saveSelectedWorkspaceId = (workspaceId: string | null) => {
  if (typeof window === "undefined") {
    return;
  }

  try {
    if (workspaceId) {
      localStorage.setItem(SELECTED_WORKSPACE_KEY, workspaceId);
    } else {
      localStorage.removeItem(SELECTED_WORKSPACE_KEY);
    }
  } catch (error) {
    console.warn("Failed to save selected workspace to localStorage:", error);
  }
};

const useStoreForWorkspaces = useStoreFor<WorkspaceState, IWorkspaceStorage>(WorkspaceState);

export const useWorkspaces = () => {
  const workspaceStore = useStoreForWorkspaces();

  const saveWorkspaces = (workspaces: Workspace[]) => {
    const currentState = workspaceStore.get();
    // Try to restore selected workspace from persisted ID if it exists in the new workspace list
    let selectedWorkspace = currentState.selectedWorkspace;

    if (!selectedWorkspace) {
      const persistedId = loadSelectedWorkspaceId();
      if (persistedId) {
        selectedWorkspace = workspaces.find((w) => w.id === persistedId) || null;
      }
    }

    workspaceStore.save(new WorkspaceState(workspaces, selectedWorkspace));
  };

  const saveSelectedWorkspace = (workspace: Workspace | null) => {
    const currentState = workspaceStore.get();
    const newState = new WorkspaceState(currentState.workspaces, workspace);
    workspaceStore.save(newState);
    // Persist the selected workspace ID to localStorage
    saveSelectedWorkspaceId(workspace?.id || null);
  };

  return { ...workspaceStore, saveWorkspaces, saveSelectedWorkspace };
};
