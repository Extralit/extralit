import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import ExtractionsGrid from "./ExtractionsGrid.client.vue";
import { WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";

const tableSpy = vi.fn(async (data: unknown) => ({ __data: data, delete: async () => undefined }));
const initSpy = vi.fn(async () => ({ table: tableSpy }));

vi.mock("~/components/v2/extractions/perspective-bootstrap", () => ({
  initPerspectiveClient: () => initSpy(),
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

describe("ExtractionsGrid", () => {
  it("boots perspective once and loads the flat projection rows into a table", async () => {
    mount(ExtractionsGrid, {
      props: { projection: PROJECTION },
      global: {
        config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
      },
    });
    await flushPromises();

    expect(initSpy).toHaveBeenCalledTimes(1);
    expect(tableSpy).toHaveBeenCalledWith([{ reference: "10.1/a", "Design.type": "RCT" }]);
  });

  it("emits load-error instead of throwing when building the Perspective table rejects", async () => {
    tableSpy.mockRejectedValueOnce(new Error("boom"));
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(ExtractionsGrid, {
      props: { projection: PROJECTION },
      global: {
        config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
      },
    });
    await flushPromises();

    expect(wrapper.emitted("load-error")).toHaveLength(1);

    consoleErrorSpy.mockRestore();
  });

  it("does not emit load-error for a superseded projection whose table build rejects after a newer one is already current", async () => {
    // Reproduces the stale-load race: P1's `client.table()` is still in flight when the user
    // switches workspace to P2, then P1 rejects *after* P2 is already `props.projection`. The
    // grid must not surface P1's failure — the page would otherwise latch `loadFailed = true`
    // for a workspace (P2) that never actually failed, and never clear it (see this file's
    // `load-error` doc comment).
    const firstCall = deferred<Awaited<ReturnType<typeof tableSpy>>>();
    tableSpy.mockImplementationOnce(() => firstCall.promise);
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const wrapper = mount(ExtractionsGrid, {
      props: { projection: PROJECTION },
      global: {
        config: { compilerOptions: { isCustomElement: (tag: string) => tag.startsWith("perspective-") } },
      },
    });
    await flushPromises();

    // Supersede P1 with P2 before P1's table build settles.
    await wrapper.setProps({ projection: PROJECTION_2 });
    await flushPromises();

    // Now P1's stale build rejects.
    firstCall.reject(new Error("boom"));
    await flushPromises();

    expect(wrapper.emitted("load-error")).toBeUndefined();
    expect(consoleErrorSpy).not.toHaveBeenCalled();

    consoleErrorSpy.mockRestore();
  });
});
