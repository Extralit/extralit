import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

const executeMock = vi.fn();
vi.mock("ts-injecty", () => ({
  useResolve: () => ({ execute: executeMock }),
}));

import { useExtractionsViewModel } from "./useExtractionsViewModel";

// Deferred promise helper — lets tests control settlement order deterministically instead of
// relying on timers or `setTimeout` scheduling.
const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

describe("useExtractionsViewModel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    executeMock.mockReset();
  });

  it("loads the projection for the override workspace id", async () => {
    const projection = new WorkspaceProjection([], [], 0);
    executeMock.mockResolvedValue(projection);

    const vm = useExtractionsViewModel("w-1");
    await vm.load();

    expect(executeMock).toHaveBeenCalledWith("w-1");
    expect(vm.projection.value).toBe(projection);
    expect(vm.loadFailed.value).toBe(false);
    expect(vm.isLoading.value).toBe(false);
  });

  it("does nothing without a workspace id", async () => {
    const vm = useExtractionsViewModel(null);
    await vm.load();
    expect(executeMock).not.toHaveBeenCalled();
  });

  it("flags load failure", async () => {
    executeMock.mockRejectedValue(new Error("boom"));
    const vm = useExtractionsViewModel("w-1");
    await vm.load();
    expect(vm.loadFailed.value).toBe(true);
  });

  it("builds the annotation URL on cell click but does not navigate (guard off)", () => {
    const vm = useExtractionsViewModel("w-1");
    const url = vm.onCellClick({ schemaId: "s-1", reference: "10.1/a b" });
    expect(url).toBe("/dataset/s-1/annotation-mode?_search=10.1%2Fa%20b");
  });

  it("keeps the last-requested workspace's result when a superseded slow response resolves later", async () => {
    const firstCall = deferred<WorkspaceProjection>();
    const secondCall = deferred<WorkspaceProjection>();
    executeMock.mockImplementation((id: string) => (id === "w-1" ? firstCall.promise : secondCall.promise));

    const { saveSelectedWorkspace } = useWorkspaces();
    saveSelectedWorkspace(new Workspace("w-1", "Workspace 1"));

    const vm = useExtractionsViewModel();
    const load1 = vm.load();

    saveSelectedWorkspace(new Workspace("w-2", "Workspace 2"));
    const load2 = vm.load();

    // Second (newer) request resolves first.
    const projectionW2 = new WorkspaceProjection([], [], 2);
    secondCall.resolve(projectionW2);
    await load2;

    // First (superseded) request resolves last — must not clobber the newer result.
    const projectionW1 = new WorkspaceProjection([], [], 1);
    firstCall.resolve(projectionW1);
    await load1;

    expect(executeMock).toHaveBeenCalledTimes(2);
    expect(vm.projection.value).toBe(projectionW2);
    expect(vm.isLoading.value).toBe(false);
    expect(vm.loadFailed.value).toBe(false);
  });

  it("does not mark loadFailed when a superseded request rejects after a newer request already succeeded", async () => {
    const firstCall = deferred<WorkspaceProjection>();
    const secondCall = deferred<WorkspaceProjection>();
    executeMock.mockImplementation((id: string) => (id === "w-1" ? firstCall.promise : secondCall.promise));

    const { saveSelectedWorkspace } = useWorkspaces();
    saveSelectedWorkspace(new Workspace("w-1", "Workspace 1"));

    const vm = useExtractionsViewModel();
    const load1 = vm.load();

    saveSelectedWorkspace(new Workspace("w-2", "Workspace 2"));
    const load2 = vm.load();

    const projectionW2 = new WorkspaceProjection([], [], 0);
    secondCall.resolve(projectionW2);
    await load2;

    firstCall.reject(new Error("boom"));
    await load1;

    expect(vm.loadFailed.value).toBe(false);
    expect(vm.projection.value).toBe(projectionW2);
  });

  it("dedupes concurrent loads for the same workspace id into a single execute call", async () => {
    const projection = new WorkspaceProjection([], [], 0);
    const pending = deferred<WorkspaceProjection>();
    executeMock.mockReturnValue(pending.promise);

    const vm = useExtractionsViewModel("w-1");
    const load1 = vm.load();
    const load2 = vm.load();

    pending.resolve(projection);
    await Promise.all([load1, load2]);

    expect(executeMock).toHaveBeenCalledTimes(1);
    expect(vm.projection.value).toBe(projection);
    expect(vm.isLoading.value).toBe(false);
    expect(vm.loadFailed.value).toBe(false);
  });
});
