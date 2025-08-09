import { Workspace } from "../entities/workspace/Workspace";
import { IWorkspaceStorage } from "../services/IWorkspaceStorage";
import { WorkspaceRepository } from "~/v1/infrastructure/repositories/WorkspaceRepository";

export class GetWorkspacesUseCase {
  constructor(
    private workspaceRepository: WorkspaceRepository,
    private workspaceStorage: IWorkspaceStorage
  ) {}

  async execute(): Promise<Workspace[]> {
    try {
      const backendWorkspaces = await this.workspaceRepository.getWorkspaces();
      const workspaces = backendWorkspaces.map((w) => new Workspace(w.id, w.name));

      // Save workspaces to storage (this will also handle restoring selected workspace from localStorage)
      this.workspaceStorage.saveWorkspaces(workspaces);

      // Get current state to check if we need auto-selection
      const currentState = (this.workspaceStorage as any).get();

      // Auto-select first workspace if none is selected and workspaces are available
      if (!currentState.selectedWorkspace && workspaces.length > 0) {
        this.workspaceStorage.saveSelectedWorkspace(workspaces[0]);
      }

      return workspaces;
    } catch (error) {
      // Enhanced error handling with fallback to cached data
      console.error("Failed to fetch workspaces:", error);

      // Check if we have cached workspaces to fall back to
      const currentState = (this.workspaceStorage as any).get();
      if (currentState.workspaces.length > 0) {
        console.warn("Using cached workspaces due to API failure");
        return currentState.workspaces;
      }

      // Re-throw error if no cached data is available
      throw new Error("Failed to fetch workspaces and no cached data available");
    }
  }

  async executeWithRetry(maxRetries = 3, retryDelay = 1000): Promise<Workspace[]> {
    try {
      const backendWorkspaces = await this.workspaceRepository.getWorkspacesWithRetry(maxRetries, retryDelay);
      const workspaces = backendWorkspaces.map((w) => new Workspace(w.id, w.name));

      // Save workspaces to storage (this will also handle restoring selected workspace from localStorage)
      this.workspaceStorage.saveWorkspaces(workspaces);

      // Get current state to check if we need auto-selection
      const currentState = (this.workspaceStorage as any).get();

      // Auto-select first workspace if none is selected and workspaces are available
      if (!currentState.selectedWorkspace && workspaces.length > 0) {
        this.workspaceStorage.saveSelectedWorkspace(workspaces[0]);
      }

      return workspaces;
    } catch (error) {
      // Enhanced error handling with fallback to cached data
      console.error("Failed to fetch workspaces with retry:", error);

      // Check if we have cached workspaces to fall back to
      const currentState = (this.workspaceStorage as any).get();
      if (currentState.workspaces.length > 0) {
        console.warn("Using cached workspaces due to API failure after retries");
        return currentState.workspaces;
      }

      // Re-throw error if no cached data is available
      throw new Error("Failed to fetch workspaces with retry and no cached data available");
    }
  }
}
