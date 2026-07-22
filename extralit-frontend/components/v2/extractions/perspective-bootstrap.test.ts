import { beforeEach, describe, expect, it, vi } from "vitest";

/**
 * `perspective-bootstrap.ts` is aliased to a stub in `vitest.config.ts` (every OTHER spec
 * that mounts `ExtractionsGrid` needs Perspective's WASM/custom-element boot kept out of the
 * happy-dom environment entirely — see that alias's comment). This spec exercises the REAL
 * module instead, by importing it with a path relative to this file (`./perspective-bootstrap`)
 * rather than the `~/components/v2/extractions/perspective-bootstrap` specifier the alias
 * matches on. The `@perspective-dev/*` packages themselves are mocked below so importing the
 * real module doesn't touch actual WASM/custom-element registration.
 */

const initServerSpy = vi.fn();
const initClientSpy = vi.fn();

vi.mock("@perspective-dev/client", () => ({
  default: {
    init_server: (...args: unknown[]) => initServerSpy(...args),
  },
}));

vi.mock("@perspective-dev/viewer", () => ({
  default: {
    init_client: (...args: unknown[]) => initClientSpy(...args),
  },
}));

vi.mock("@perspective-dev/viewer-datagrid", () => ({}));

vi.mock("@perspective-dev/server/dist/wasm/perspective-server.wasm?url", () => ({ default: "server.wasm" }));
vi.mock("@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url", () => ({ default: "viewer.wasm" }));

beforeEach(() => {
  vi.resetModules();
  initServerSpy.mockReset();
  initClientSpy.mockReset();
  // Real `fetch(SERVER_WASM)`/`fetch(CLIENT_WASM)` calls are made with plain mock-string
  // "URLs" as arguments (see the wasm `?url` mocks above) regardless of whether
  // `init_server`/`init_client` themselves are mocked, since `fetch(...)` is evaluated as an
  // argument expression before either is called. Stubbing `fetch` avoids both a real network
  // attempt and an unhandled-rejection warning from an un-awaited failed URL parse.
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({}))
  );
});

describe("initPerspective", () => {
  it("resets the memoized boot promise on rejection so the next call retries instead of replaying the same failure", async () => {
    initServerSpy.mockImplementationOnce(() => Promise.reject(new Error("network blip")));
    initServerSpy.mockImplementation(() => Promise.resolve(undefined));
    initClientSpy.mockImplementation(() => Promise.resolve(undefined));

    const { initPerspective } = await import("./perspective-bootstrap");

    await expect(initPerspective()).rejects.toThrow("network blip");
    // Without the fix, `ready` stays set to the rejected promise forever (`ready ??= ...`
    // never reassigns once `ready` is non-null, rejected or not), so this second call would
    // reject with the SAME "network blip" error instead of resolving.
    await expect(initPerspective()).resolves.toBeDefined();
    expect(initServerSpy).toHaveBeenCalledTimes(2);
  });

  it("propagates the rejection to every caller sharing the failed in-flight attempt", async () => {
    initServerSpy.mockImplementation(() => Promise.reject(new Error("network blip")));
    initClientSpy.mockImplementation(() => Promise.resolve(undefined));

    const { initPerspective } = await import("./perspective-bootstrap");

    const [a, b] = await Promise.allSettled([initPerspective(), initPerspective()]);
    expect(a.status).toBe("rejected");
    expect(b.status).toBe("rejected");
    // Both callers raced the SAME attempt, so only one underlying boot should have run.
    expect(initServerSpy).toHaveBeenCalledTimes(1);
  });

  it("initializes exactly once across concurrent and sequential calls on a successful boot", async () => {
    initServerSpy.mockImplementation(() => Promise.resolve(undefined));
    initClientSpy.mockImplementation(() => Promise.resolve(undefined));

    const { initPerspective } = await import("./perspective-bootstrap");

    const [a, b] = await Promise.all([initPerspective(), initPerspective()]);
    const c = await initPerspective();

    expect(a).toBe(b);
    expect(b).toBe(c);
    expect(initServerSpy).toHaveBeenCalledTimes(1);
    expect(initClientSpy).toHaveBeenCalledTimes(1);
  });
});
