import { Workspace } from "../entities/workspace/Workspace";

export interface IWorkspaceStorage {
  saveWorkspaces(workspaces: Workspace[]): void;
  saveSelectedWorkspace(workspace: Workspace | null): void;
}
