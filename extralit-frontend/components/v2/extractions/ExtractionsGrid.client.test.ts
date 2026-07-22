import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExtractionsGrid from "./ExtractionsGrid.client.vue";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

// Module-level so the `vi.mock` factory below (evaluated once, hoisted) can close over them.
// Call counts and implementations are reset/re-established per spec in `beforeEach` — without
// that, `toHaveBeenCalledTimes(N)` assertions only pass because of spec execution order, and a
// `mockImplementationOnce`/`mockRejectedValueOnce` installed by one spec but left unconsumed
// (e.g. by an early failure) could otherwise leak into the next spec's first call.
const tableSpy = vi.fn();
const defaultTableImpl = async (data: unknown) => ({ __data: data, delete: async () => undefined });

// Mocks the shared client factory `initPerspectiveClient` (not, despite the name similarity,
// the Perspective WASM boot itself — that happens inside the real implementation this spy
// replaces; see perspective-bootstrap.ts).
const initPerspectiveClientSpy = vi.fn();
const defaultInitPerspectiveClientImpl = async () => ({ table: tableSpy });

vi.mock("~/components/v2/extractions/perspective-bootstrap", () => ({
  initPerspectiveClient: () => initPerspectiveClientSpy(),
}));

const PROJECTION = new WorkspaceProjection(
  [
    {
      name: "Design.type",
      schemaId: "s-1",
      schemaName: "Design",
      questionName: "type",
      subColumn: null,
      dtype: "text",
    },
  ],
  [
    {
      reference: "10.1/a",
      rowIndex: 0,
      cells: {
        "Design.type": { value: "RCT", source: "response", recordId: "r-1", agent: null, score: null },
      },
    },
  ],
  1
);

// A distinct instance (referential inequality from PROJECTION matters — see the superseded-load
// test below) representing the workspace the user switches to mid-load.
const PROJECTION_2 = new WorkspaceProjection(
  [
    {
      name: "Design.type",
      schemaId: "s-2",
      schemaName: "Design",
      questionName: "type",
      subColumn: null,
      dtype: "text",
    },
  ],
  [
    {
      reference: "10.2/b",
      rowIndex: 0,
      cells: {
        "Design.type": { value: "Cohort", source: "response", recordId: "r-2", agent: null, score: null },
      },
    },
  ],
  1
);

// Deferred promise helper — lets this suite control settlement order deterministically (mirrors
// the identical helper in useExtractionsViewModel.test.ts).
const deferred = <T>() => {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
};

const mountGrid = (projection: WorkspaceProjection) =>
  mount(ExtractionsGrid, {
    props: { projection },
    global: {
      config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
    },
  });

let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

describe("ExtractionsGrid", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    tableSpy.mockImplementation(defaultTableImpl);
    initPerspectiveClientSpy.mockImplementation(defaultInitPerspectiveClientImpl);
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it("boots perspective once and loads the flat projection rows into a table", async () => {
    mountGrid(PROJECTION);
    await flushPromises();

    expect(initPerspectiveClientSpy).toHaveBeenCalledTimes(1);
    expect(tableSpy).toHaveBeenCalledWith([{ reference: "10.1/a", "Design.type": "RCT" }]);
  });

  it("emits load-error instead of throwing when building the Perspective table rejects", async () => {
    tableSpy.mockRejectedValueOnce(new Error("boom"));

    const wrapper = mountGrid(PROJECTION);
    await flushPromises();

    expect(wrapper.emitted("load-error")).toHaveLength(1);
  });

  it("does not emit load-error for a superseded projection whose table build rejects after a newer one is already current", async () => {
    // Reproduces the stale-load race: P1's `client.table()` is still in flight when the user
    // switches workspace to P2, then P1 rejects *after* P2 is already `props.projection`. The
    // grid must not surface P1's failure — the page would otherwise latch `loadFailed = true`
    // for a workspace (P2) that never actually failed, and never clear it (see this file's
    // `load-error` doc comment).
    const firstCall = deferred<Awaited<ReturnType<typeof tableSpy>>>();
    tableSpy.mockImplementationOnce(() => firstCall.promise);

    const wrapper = mountGrid(PROJECTION);
    await flushPromises();

    // Supersede P1 with P2 before P1's table build settles.
    await wrapper.setProps({ projection: PROJECTION_2 });
    await flushPromises();

    // Now P1's stale build rejects.
    firstCall.reject(new Error("boom"));
    await flushPromises();

    expect(wrapper.emitted("load-error")).toBeUndefined();
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it("emits load-error when the viewer's load/restore/getPlugin chain rejects, not just when client.table() rejects", async () => {
    // Finding 2: the second `try`/`catch` in `performLoad` (wrapping `viewer.eject()`,
    // `viewer.load()`, `viewer.restore()`, `getPlugin()`) previously had a bare `catch {}` that
    // swallowed everything silently. happy-dom never upgrades `<perspective-viewer>`, so that
    // code is normally unreachable (`viewer?.load` stays undefined and `performLoad` returns
    // before the `try`) — reached here the same way the component itself would call it, by
    // installing stub methods directly on the actual DOM node standing in for the upgraded
    // custom element, exactly mirroring what a real `load()`/`restore()` rejection looks like.
    const wrapper = mountGrid(PROJECTION);
    const viewerNode = wrapper.element as unknown as {
      load: (...args: unknown[]) => Promise<unknown>;
      restore: (...args: unknown[]) => Promise<unknown>;
      getPlugin: (...args: unknown[]) => Promise<unknown>;
      addEventListener: (...args: unknown[]) => void;
      removeEventListener: (...args: unknown[]) => void;
    };
    viewerNode.load = vi.fn(async () => undefined);
    viewerNode.restore = vi.fn(async () => {
      throw new Error("viewer restore failed");
    });
    viewerNode.getPlugin = vi.fn(async () => undefined);
    viewerNode.addEventListener = vi.fn();
    viewerNode.removeEventListener = vi.fn();

    await flushPromises();

    expect(wrapper.emitted("load-error")).toHaveLength(1);
    expect(consoleErrorSpy).toHaveBeenCalled();
  });

  it("releases the table built for a superseded projection even when the viewer never upgrades (deterministic-leak fix)", async () => {
    // Finding 3: `table = newTable` drops the last reference to the previous table, and the
    // `!viewer?.load` early-return guard used to return before that previous table was ever
    // deleted. Under happy-dom the custom element never upgrades, so every call takes this
    // exact guard — this is the deterministic leak Finding 3 describes, naturally reachable
    // (no monkey-patching needed) via two ordinary, successful, back-to-back loads.
    const firstDelete = vi.fn(async () => undefined);
    const secondDelete = vi.fn(async () => undefined);
    tableSpy.mockImplementationOnce(async (data: unknown) => ({ __data: data, delete: firstDelete }));
    tableSpy.mockImplementationOnce(async (data: unknown) => ({ __data: data, delete: secondDelete }));

    const wrapper = mountGrid(PROJECTION);
    await flushPromises();

    await wrapper.setProps({ projection: PROJECTION_2 });
    await flushPromises();

    expect(firstDelete).toHaveBeenCalledTimes(1);
    expect(secondDelete).not.toHaveBeenCalled();
  });
});
