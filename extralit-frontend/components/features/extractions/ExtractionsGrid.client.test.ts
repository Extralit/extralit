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

vi.mock("~/components/features/extractions/perspective-bootstrap", () => ({
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
    // `fakeRegularTable` appends a shadow host to `document.body` and nothing unmounts it.
    // happy-dom shares one document across every spec in the file, so without this the hosts
    // (and their shadow roots) accumulate and the next spec to query `document` for a `<style>`
    // or a `<td>` sees leftovers from earlier ones.
    document.body.innerHTML = "";
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

  describe("cell styling", () => {
    // The banding/pointer affordances are the two things the shadow-DOM style fix exists for,
    // and neither was reachable by any spec: under happy-dom `getPlugin` resolves to
    // `undefined`, so `regularTable` stays null and `ensureShadowStyles`/`applyCellStyles`
    // never run. Stubbing `getPlugin` with a fake `regular_table` living in a REAL
    // `attachShadow` root makes both assertable — including the property that broke twice in
    // review: that the classes land on the FIRST draw, with no redraw and without the
    // style listener ever firing.
    const BANDING_PROJECTION = new WorkspaceProjection(
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
        // Second reference: `bandParity` flips on reference change, so this row bands while
        // row 0 does not. Its cell is absent, so it is also the not-linkable case.
        { reference: "10.2/b", rowIndex: 0, cells: {} },
      ],
      2
    );

    /**
     * A fake `regular-table`: a real element inside a real open shadow root, carrying one
     * `<td>` per (row, column) plus a `<th>` standing in for a row header, with `getMeta`
     * returning the metadata shapes regular-table emits for each.
     */
    const fakeRegularTable = () => {
      const host = document.createElement("div");
      document.body.appendChild(host);
      const shadow = host.attachShadow({ mode: "open" });
      const rt = document.createElement("div");
      shadow.appendChild(rt);

      const meta = new Map<Element, Record<string, unknown>>();
      const makeCell = (tag: "td" | "th", cellMeta: Record<string, unknown>) => {
        const cell = document.createElement(tag);
        rt.appendChild(cell);
        meta.set(cell, cellMeta);
        return cell;
      };

      const row0 = makeCell("td", { type: "body", y: 0, column_header: ["Design.type"] });
      const row1 = makeCell("td", { type: "body", y: 1, column_header: ["Design.type"] });
      // A row header: same `HTMLTableCellElement` interface, but `type: "row_header"` — it
      // must never be banded against a body row's parity.
      const rowHeader = makeCell("th", { type: "row_header", y: 1, row_header: ["10.2/b"] });

      const styleListener = vi.fn();
      Object.assign(rt, {
        getMeta: (cell: Element) => meta.get(cell),
        addStyleListener: (callback: unknown) => {
          styleListener(callback);
          return () => undefined;
        },
      });

      return { host, shadow, rt, row0, row1, rowHeader, styleListener };
    };

    const mountWithPlugin = async (table: ReturnType<typeof fakeRegularTable>) => {
      const wrapper = mountGrid(BANDING_PROJECTION);
      const viewerNode = wrapper.element as unknown as Record<string, unknown>;
      viewerNode.load = vi.fn(async () => undefined);
      viewerNode.restore = vi.fn(async () => undefined);
      viewerNode.eject = vi.fn(async () => undefined);
      viewerNode.getPlugin = vi.fn(async () => ({ regular_table: table.rt }));
      viewerNode.addEventListener = vi.fn();
      viewerNode.removeEventListener = vi.fn();
      await flushPromises();
      return wrapper;
    };

    it("bands the second reference's cells and marks populated cells linkable on the first draw, without waiting for a redraw", async () => {
      const table = fakeRegularTable();
      await mountWithPlugin(table);

      // Row 0 is the first reference (parity 0); row 1 is the second (parity 1).
      expect(table.row0.classList.contains("extractions-grid__band")).toBe(false);
      expect(table.row1.classList.contains("extractions-grid__band")).toBe(true);

      // `Design.type` is populated on row 0 only, so only that cell advertises clickability.
      expect(table.row0.classList.contains("extractions-grid__linkable")).toBe(true);
      expect(table.row1.classList.contains("extractions-grid__linkable")).toBe(false);

      // The crux: this all happened on the explicit first-paint `applyCellStyles` call.
      // `addStyleListener` only registers a callback — it neither invokes it nor forces a
      // redraw — so without that explicit call nothing would be styled until a scroll or
      // resize, i.e. never for a user who just reads the grid.
      expect(table.styleListener).toHaveBeenCalledTimes(1);
      const registeredCallback = table.styleListener.mock.calls[0][0];
      expect(registeredCallback).toBeTypeOf("function");
    });

    // NOTE: there is deliberately no "row headers are never banded" spec here. Three
    // independent mechanisms already guarantee it — `applyCellStyles` scopes to
    // `querySelectorAll("td")`, `cellMetaAt` rejects `type !== "body"`, and a real row
    // header's metadata carries `row_header`/`row_header_x` rather than the `column_header`
    // the name resolution requires. Mutation-testing confirmed no such spec can fail even
    // with the first two removed, so it would assert nothing. See `cellMetaAt`'s comment.

    it("injects the cell stylesheet into the shadow root exactly once across repeated loads", async () => {
      const table = fakeRegularTable();
      const wrapper = await mountWithPlugin(table);

      const styles = () => table.shadow.querySelectorAll("style#extractions-grid-cell-style");
      expect(styles()).toHaveLength(1);
      // Document-level CSS (including this component's Vue `:deep()` rules) cannot cross a
      // shadow boundary, which is why the rules are injected here at all.
      expect(styles()[0].textContent).toContain("extractions-grid__band");

      await wrapper.setProps({ projection: PROJECTION });
      await flushPromises();

      // Id-guarded: a second load must not append a duplicate.
      expect(styles()).toHaveLength(1);
    });
  });
});
