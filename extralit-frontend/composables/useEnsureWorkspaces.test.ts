import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const execute = vi.fn(async () => [{ id: "w-1", name: "e2e-v2" }]);
vi.mock("ts-injecty", () => ({ useResolve: () => ({ execute }) }));

import { useEnsureWorkspaces } from "./useEnsureWorkspaces";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

describe("useEnsureWorkspaces", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    execute.mockClear();
  });

  it("fetches workspaces when the store is empty", async () => {
    const { ensureWorkspaces } = useEnsureWorkspaces();
    await ensureWorkspaces();
    expect(execute).toHaveBeenCalledOnce();
  });

  it("does not refetch when workspaces are already loaded", async () => {
    useWorkspaces().saveWorkspaces([{ id: "w-1", name: "e2e-v2" } as never]);
    const { ensureWorkspaces } = useEnsureWorkspaces();
    await ensureWorkspaces();
    expect(execute).not.toHaveBeenCalled();
  });
});
