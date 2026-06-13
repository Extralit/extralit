import type { AxiosInstance } from "axios";
import { type Response } from "../types";
import { mediumCache, revalidateCache } from "./AxiosCache";

interface BackendWorkspace {
  id: string;
  name: string;
}

const enum WORKSPACES_API_ERRORS {
  GET_WORKSPACES = "GET_WORKSPACES",
  CREATE_WORKSPACE = "CREATE_WORKSPACE",
  NETWORK_ERROR = "NETWORK_ERROR",
  UNAUTHORIZED = "UNAUTHORIZED",
  SERVER_ERROR = "SERVER_ERROR",
}

export class WorkspaceRepositoryError extends Error {
  constructor(public readonly type: WORKSPACES_API_ERRORS, public readonly originalError: any, message?: string) {
    super(message || `Workspace API error: ${type}`);
    this.name = "WorkspaceRepositoryError";
  }
}

export class WorkspaceRepository {
  constructor(private readonly axios: AxiosInstance) {}

  async getWorkspaces(): Promise<BackendWorkspace[]> {
    try {
      const { data } = await this.axios.get<Response<BackendWorkspace[]>>("/v1/me/workspaces", mediumCache());

      return data.items;
    } catch (err: any) {
      const errorType = this.categorizeError(err);
      throw new WorkspaceRepositoryError(errorType, err, this.getErrorMessage(errorType, err));
    }
  }

  async getWorkspacesWithRetry(maxRetries = 3, retryDelay = 1000): Promise<BackendWorkspace[]> {
    let lastError: WorkspaceRepositoryError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await this.getWorkspaces();
      } catch (error) {
        lastError = error as WorkspaceRepositoryError;

        // Don't retry for certain error types
        if (lastError.type === WORKSPACES_API_ERRORS.UNAUTHORIZED) {
          throw lastError;
        }

        if (attempt < maxRetries) {
          console.warn(`Workspace API retry attempt ${attempt} failed:`, error);
          await new Promise((resolve) => setTimeout(resolve, retryDelay * attempt));
        }
      }
    }

    throw lastError!;
  }

  async create(name: string): Promise<BackendWorkspace> {
    try {
      const { data } = await this.axios.post<BackendWorkspace>("/v1/workspaces", {
        name,
      });

      revalidateCache("/v1/me/workspaces");

      return data;
    } catch (err: any) {
      const errorType = this.categorizeError(err);
      throw new WorkspaceRepositoryError(errorType, err, this.getErrorMessage(errorType, err));
    }
  }

  private categorizeError(error: any): WORKSPACES_API_ERRORS {
    if (!error.response) {
      return WORKSPACES_API_ERRORS.NETWORK_ERROR;
    }

    const status = error.response.status;

    if (status === 401 || status === 403) {
      return WORKSPACES_API_ERRORS.UNAUTHORIZED;
    }

    if (status >= 500) {
      return WORKSPACES_API_ERRORS.SERVER_ERROR;
    }

    // Default to GET_WORKSPACES for other errors
    return WORKSPACES_API_ERRORS.GET_WORKSPACES;
  }

  private getErrorMessage(errorType: WORKSPACES_API_ERRORS, _originalError: any): string {
    switch (errorType) {
      case WORKSPACES_API_ERRORS.NETWORK_ERROR:
        return "Network error occurred while fetching workspaces. Please check your connection.";
      case WORKSPACES_API_ERRORS.UNAUTHORIZED:
        return "You are not authorized to access workspaces. Please log in again.";
      case WORKSPACES_API_ERRORS.SERVER_ERROR:
        return "Server error occurred while fetching workspaces. Please try again later.";
      case WORKSPACES_API_ERRORS.GET_WORKSPACES:
        return "Failed to fetch workspaces. Please try again.";
      case WORKSPACES_API_ERRORS.CREATE_WORKSPACE:
        return "Failed to create workspace. Please try again.";
      default:
        return "An unexpected error occurred.";
    }
  }
}
