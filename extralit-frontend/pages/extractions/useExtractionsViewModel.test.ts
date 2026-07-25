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

  it("starts with hasLoaded false and flips it true once the first load settles, so the empty state cannot flash before the first load", async () => {
    const projection = new WorkspaceProjection([], [], 0);
    const pending = deferred<WorkspaceProjection>();
    executeMock.mockReturnValue(pending.promise);

    const vm = useExtractionsViewModel("w-1");
    // Without the `hasLoaded` fix, this is already `true` (it's never initialized `false`, or
    // the page gates the empty state on `isLoading` alone) — which is exactly what lets the
    // empty state render on first paint before the spinner ever shows.
    expect(vm.hasLoaded.value).toBe(false);

    const load1 = vm.load();
    expect(vm.hasLoaded.value).toBe(false);

    pending.resolve(projection);
    await load1;

    expect(vm.hasLoaded.value).toBe(true);
  });

  it("clears the stale projection when the workspace is deselected mid-flight, so a superseded response cannot repopulate it after the fact", async () => {
    const firstCall = deferred<WorkspaceProjection>();
    executeMock.mockReturnValue(firstCall.promise);

    const { saveSelectedWorkspace } = useWorkspaces();
    saveSelectedWorkspace(new Workspace("w-1", "Workspace 1"));

    const vm = useExtractionsViewModel();
    const load1 = vm.load();
    expect(vm.isLoading.value).toBe(true);

    // Deselect the workspace entirely while the load is still in flight.
    saveSelectedWorkspace(null);
    const load2 = vm.load();
    await load2;

    // Without the fix, `load()` returns immediately on a null id without bumping
    // `requestToken`, so the still-in-flight `load1`'s `token === requestToken` check still
    // passes when it resolves below — committing a projection for a workspace the user has
    // already left, with `isLoading` cleared and no way to tell the grid is now stale.
    expect(vm.projection.value).toBeNull();
    expect(vm.isLoading.value).toBe(false);

    const staleProjection = new WorkspaceProjection([], [], 1);
    firstCall.resolve(staleProjection);
    await load1;

    expect(vm.projection.value).toBeNull();
  });

  it("reselecting the same workspace mid-flight issues a fresh request instead of adopting the superseded one", async () => {
    const firstCall = deferred<WorkspaceProjection>();
    const secondCall = deferred<WorkspaceProjection>();
    executeMock.mockReturnValueOnce(firstCall.promise).mockReturnValueOnce(secondCall.promise);

    const { saveSelectedWorkspace } = useWorkspaces();
    const workspace = new Workspace("w-1", "Workspace 1");
    saveSelectedWorkspace(workspace);

    const vm = useExtractionsViewModel();
    const load1 = vm.load();

    // Deselect, then reselect the *same* workspace while the original load is still running.
    // Both are ordinary workspace-selector firings.
    saveSelectedWorkspace(null);
    await vm.load();
    saveSelectedWorkspace(workspace);
    const load3 = vm.load();

    // Without the currency check in the dedupe guard, `inFlight.workspaceId === "w-1"` still
    // matches, so this reselect hands back the superseded promise and issues no request at
    // all. That promise then fails its own token check, assigns no projection and never sets
    // `isLoading` — leaving the page on "no extracted references" for a workspace with data.
    expect(executeMock).toHaveBeenCalledTimes(2);

    const staleProjection = new WorkspaceProjection([], [], 1);
    firstCall.resolve(staleProjection);
    await load1;
    expect(vm.projection.value).toBeNull();

    const freshProjection = new WorkspaceProjection([], [], 7);
    secondCall.resolve(freshProjection);
    await load3;

    expect(vm.projection.value).toBe(freshProjection);
    expect(vm.isLoading.value).toBe(false);
  });

  it("flags load failure", async () => {
    executeMock.mockRejectedValue(new Error("boom"));
    const vm = useExtractionsViewModel("w-1");
    await vm.load();
    expect(vm.loadFailed.value).toBe(true);
  });

  // NOTE: no spec here for `onCellClick`'s guarded navigation. One was tried and removed:
  // its only assertion was on the returned URL — byte-identical to grid-adapter.test.ts's
  // `buildAnnotationUrl` case — while its actual claim ("does not navigate") went
  // unasserted, so flipping ANNOTATION_CELL_LINKS_ENABLED to true, or deleting the guard
  // outright, both left it green. Covering it for real needs a `window.location` spy, and
  // belongs with the ENG-32 consumer that makes navigation reachable.

  it("flags load failure when the grid reports a load-error after a successful projection load", async () => {
    // Reproduces ExtractionsGrid's `load-error` emit (e.g. `client.table()` rejecting on a
    // non-scalar cell value): the projection itself loaded fine, but the page's state
    // cascade must still fall back to the loadError message instead of leaving the grid
    // mounted empty with no explanation.
    const projection = new WorkspaceProjection([], [], 0);
    executeMock.mockResolvedValue(projection);

    const vm = useExtractionsViewModel("w-1");
    await vm.load();
    expect(vm.loadFailed.value).toBe(false);

    vm.onGridLoadError();

    expect(vm.loadFailed.value).toBe(true);
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

  it("dedupes a w-1 load that ping-pongs back (w-1 -> w-2 -> w-1 -> w-1) against the still-pending later w-1 request", async () => {
    // Reproduces: oldest w-1 call's `finally` must not clear a newer generation's `inFlight`
    // entry just because it shares the same workspace id. Sequence: w-1 (gen A) -> w-2
    // (evicts gen A's entry) -> w-1 (gen B, a genuinely new request since gen A's entry is
    // gone) -> gen A settles -> a 4th w-1 load must dedupe against gen B, still pending.
    const w1GenA = deferred<WorkspaceProjection>();
    const w2Call = deferred<WorkspaceProjection>();
    const w1GenB = deferred<WorkspaceProjection>();
    const w1Calls = [w1GenA, w1GenB];
    // If the dedup defect lets a redundant w-1 call through, resolve it immediately (rather
    // than with a never-settled deferred) so the test fails on the call-count assertion
    // instead of hanging on an unresolved `await`.
    const unexpectedExtraCall = new WorkspaceProjection([], [], -1);
    executeMock.mockImplementation((id: string) => {
      if (id !== "w-1") return w2Call.promise;
      const next = w1Calls.shift();
      return next ? next.promise : Promise.resolve(unexpectedExtraCall);
    });

    const { saveSelectedWorkspace } = useWorkspaces();
    saveSelectedWorkspace(new Workspace("w-1", "Workspace 1"));

    const vm = useExtractionsViewModel();
    const load1 = vm.load(); // w-1 gen A — creates inFlight{w-1, gen A}

    saveSelectedWorkspace(new Workspace("w-2", "Workspace 2"));
    const load2 = vm.load(); // w-2 — id mismatch, evicts gen A's entry, inFlight{w-2}

    saveSelectedWorkspace(new Workspace("w-1", "Workspace 1"));
    const load3 = vm.load(); // w-1 gen B — id mismatch against inFlight{w-2}, a real 3rd call

    expect(executeMock).toHaveBeenCalledTimes(3);

    // Oldest w-1 call (gen A) settles while gen B is still in flight. Buggy code clears
    // `inFlight` here because it only compares `workspaceId === 'w-1'`, which also matches
    // gen B's still-pending entry.
    const projectionGenA = new WorkspaceProjection([], [], 1);
    w1GenA.resolve(projectionGenA);
    await load1;

    // A 4th w-1 load must dedupe against gen B (still pending), not fire a redundant call.
    const load4 = vm.load();
    expect(executeMock).toHaveBeenCalledTimes(3);

    const projectionGenB = new WorkspaceProjection([], [], 2);
    w1GenB.resolve(projectionGenB);
    await load3;
    await load4;

    const projectionW2 = new WorkspaceProjection([], [], 0);
    w2Call.resolve(projectionW2);
    await load2;

    // gen B is the last-requested (highest token) call, so its result wins.
    expect(executeMock).toHaveBeenCalledTimes(3);
    expect(vm.projection.value).toBe(projectionGenB);
    expect(vm.isLoading.value).toBe(false);
    expect(vm.loadFailed.value).toBe(false);
  });
});
