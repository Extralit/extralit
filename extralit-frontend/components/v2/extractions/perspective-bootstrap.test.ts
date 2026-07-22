import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `perspective-bootstrap.ts` is aliased to a stub in `vitest.config.ts` (every OTHER spec
 * that mounts `ExtractionsGrid` needs Perspective's WASM/custom-element boot kept out of the
 * happy-dom environment entirely — see that alias's comment). This spec exercises the REAL
 * module instead, by importing it with a path relative to this file (`./perspective-bootstrap`)
 * rather than the `~/components/v2/extractions/perspective-bootstrap` specifier the alias
 * matches on. The `@perspective-dev/*` packages themselves are mocked below so importing the
 * real module doesn't touch actual WASM/custom-element registration.
 *
 * The mock factories are typed against the real modules' `.d.ts` signatures (confirmed against
 * the installed package — `@perspective-dev/client/dist/esm/perspective.browser.d.ts`'s
 * `init_server(...): void` and `@perspective-dev/viewer/dist/esm/bootstrap.d.ts`'s
 * `init_client(...): Promise<void>`) via `satisfies Partial<typeof import(...)>` so a future
 * signature change that silently reintroduces this bug (`init_server` starting to look like it
 * returns a promise, or vice versa) fails typecheck here rather than only in production.
 */

const initServerSpy = vi.fn<(...args: unknown[]) => void>();
const initClientSpy = vi.fn<(...args: unknown[]) => Promise<void>>();
const workerSpy = vi.fn();

vi.mock("@perspective-dev/client", () => {
  const mod = {
    init_server: (...args: unknown[]) => initServerSpy(...args),
    worker: (...args: unknown[]) => workerSpy(...args),
  } satisfies Partial<typeof import("@perspective-dev/client")>;
  return { default: mod };
});

vi.mock("@perspective-dev/viewer", () => {
  const mod = {
    init_client: (...args: unknown[]) => initClientSpy(...args),
  } satisfies Partial<typeof import("@perspective-dev/viewer")>;
  return { default: mod };
});

vi.mock("@perspective-dev/viewer-datagrid", () => ({}));

vi.mock("@perspective-dev/server/dist/wasm/perspective-server.wasm?url", () => ({ default: "server.wasm" }));
vi.mock("@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url", () => ({ default: "viewer.wasm" }));

const fetchMock = vi.fn();

beforeEach(() => {
  vi.resetModules();
  initServerSpy.mockReset();
  initClientSpy.mockReset();
  workerSpy.mockReset();
  fetchMock.mockReset();
  // Production's actual retry-on-rejection trigger: a rejected `fetch(SERVER_WASM)` (or
  // `fetch(CLIENT_WASM)`), NOT a rejected `init_server`/`init_client` call — `init_server`
  // returns `void` in the real module, so it can never itself be the thing that rejects.
  fetchMock.mockImplementation(async () => ({ ok: true }));
  vi.stubGlobal("fetch", fetchMock);
});

describe("initPerspective", () => {
  it("resets the memoized boot promise when fetch(SERVER_WASM) rejects, so the next call retries instead of replaying the same failure", async () => {
    fetchMock.mockImplementationOnce(async () => {
      throw new Error("network blip");
    });
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementation(() => Promise.resolve());

    const { initPerspective } = await import("./perspective-bootstrap");

    // Without the fix, `Promise.all([init_server(fetch(...)), init_client(fetch(...))])`
    // settles on the viewer half alone — a rejected server-WASM fetch never reaches `attempt`,
    // so this first call would resolve (falsely reporting a successful boot) instead of
    // rejecting, and the rejected `fetch` would surface later as an unhandled rejection.
    await expect(initPerspective()).rejects.toThrow("network blip");
    // Without the fix, `ready` stays set forever once non-null, so this second call would
    // reject with the SAME "network blip" error (or, pre-fix, spuriously resolve) instead of
    // performing a fresh, successful retry.
    await expect(initPerspective()).resolves.toBeDefined();
    expect(fetchMock).toHaveBeenCalledTimes(4); // 2 wasm fetches x 2 attempts
    expect(initServerSpy).toHaveBeenCalledTimes(1); // only the successful attempt reaches init_server
  });

  it("resets the memoized boot promise when init_client rejects, so the next call retries instead of replaying the same failure", async () => {
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementationOnce(() => Promise.reject(new Error("client init failed")));
    initClientSpy.mockImplementation(() => Promise.resolve());

    const { initPerspective } = await import("./perspective-bootstrap");

    await expect(initPerspective()).rejects.toThrow("client init failed");
    await expect(initPerspective()).resolves.toBeDefined();
    expect(initClientSpy).toHaveBeenCalledTimes(2);
  });

  it("propagates the rejection to every caller sharing the failed in-flight attempt", async () => {
    fetchMock.mockImplementation(async () => {
      throw new Error("network blip");
    });
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementation(() => Promise.resolve());

    const { initPerspective } = await import("./perspective-bootstrap");

    const [a, b] = await Promise.allSettled([initPerspective(), initPerspective()]);
    expect(a.status).toBe("rejected");
    expect(b.status).toBe("rejected");
    // Both callers raced the SAME attempt, so only one underlying fetch pair should have run.
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("initializes exactly once across concurrent and sequential calls on a successful boot, and a later call reuses the memo without re-running the boot", async () => {
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementation(() => Promise.resolve());

    const { initPerspective } = await import("./perspective-bootstrap");

    const [a, b] = await Promise.all([initPerspective(), initPerspective()]);
    const c = await initPerspective();

    expect(a).toBe(b);
    expect(b).toBe(c);
    expect(initServerSpy).toHaveBeenCalledTimes(1);
    expect(initClientSpy).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // A resolved boot is never reset: a THIRD call after the successful retry-free run above
    // must still reuse the same memoized promise instead of re-running init_server/init_client.
    const d = await initPerspective();
    expect(d).toBe(c);
    expect(initServerSpy).toHaveBeenCalledTimes(1);
    expect(initClientSpy).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe("initPerspectiveClient", () => {
  it("resets the memoized client promise on rejection so the next call retries instead of replaying the same failure", async () => {
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementation(() => Promise.resolve());
    workerSpy.mockImplementationOnce(() => Promise.reject(new Error("worker boot failed")));
    workerSpy.mockImplementation(() => Promise.resolve({ marker: "client" }));

    const { initPerspectiveClient } = await import("./perspective-bootstrap");

    await expect(initPerspectiveClient()).rejects.toThrow("worker boot failed");
    await expect(initPerspectiveClient()).resolves.toEqual({ marker: "client" });
    expect(workerSpy).toHaveBeenCalledTimes(2);
  });

  it("shares exactly one client across concurrent and sequential calls, calling perspective.worker() exactly once", async () => {
    initServerSpy.mockImplementation(() => undefined);
    initClientSpy.mockImplementation(() => Promise.resolve());
    workerSpy.mockImplementation(() => Promise.resolve({ marker: "client" }));

    const { initPerspectiveClient } = await import("./perspective-bootstrap");

    const [a, b] = await Promise.all([initPerspectiveClient(), initPerspectiveClient()]);
    const c = await initPerspectiveClient();

    expect(a).toBe(b);
    expect(b).toBe(c);
    // This is the crux of the worker/WASM-heap leak fix: every mount of `ExtractionsGrid`
    // must share this ONE client rather than each calling `perspective.worker()` (which
    // constructs a brand-new Web Worker + WASM server instance every time) for itself.
    expect(workerSpy).toHaveBeenCalledTimes(1);
  });
});
