import type { AxiosInstance } from "axios";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceRepository } from "./WorkspaceRepository";

const BACKEND_WORKSPACE = {
  id: "ws-1",
  name: "my-workspace",
  inserted_at: "2026-01-01T00:00:00",
  updated_at: "2026-01-02T00:00:00",
};

const axiosMock = (impl: { get?: unknown; post?: unknown }) =>
  ({
    get: vi.fn(async () => ({ data: impl.get })),
    post: vi.fn(async () => ({ data: impl.post })),
  }) as unknown as AxiosInstance;

describe("WorkspaceRepository", () => {
  it("unwraps the items envelope when listing workspaces", async () => {
    const axios = axiosMock({ get: { items: [BACKEND_WORKSPACE] } });

    const workspaces = await new WorkspaceRepository(axios).getWorkspaces();

    expect(axios.get).toHaveBeenCalledWith("/v1/me/workspaces", expect.anything());
    expect(workspaces).toEqual([BACKEND_WORKSPACE]);
  });

  it("returns the created workspace", async () => {
    const axios = axiosMock({ post: BACKEND_WORKSPACE });

    const created = await new WorkspaceRepository(axios).create("my-workspace");

    expect(axios.post).toHaveBeenCalledWith("/v1/workspaces", { name: "my-workspace" });
    expect(created).toEqual(BACKEND_WORKSPACE);
  });

  it("surfaces a typed error when the request fails", async () => {
    const axios = {
      get: vi.fn(async () => {
        throw { response: { status: 401 } };
      }),
    } as unknown as AxiosInstance;

    await expect(new WorkspaceRepository(axios).getWorkspaces()).rejects.toMatchObject({
      type: "UNAUTHORIZED",
    });
  });
});
