import perspective from "@perspective-dev/client";
import perspective_viewer from "@perspective-dev/viewer";
import "@perspective-dev/viewer-datagrid";
import SERVER_WASM from "@perspective-dev/server/dist/wasm/perspective-server.wasm?url";
import CLIENT_WASM from "@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url";

// SPA (ssr: false): this runs client-side only. Module-level guard so the WASM engines
// initialize exactly once no matter how often the page remounts (spec §3.3).
//
// `ready` memoizes the boot promise so concurrent callers (e.g. two fast remounts) share one
// in-flight WASM init instead of racing multiple `init_server`/`init_client` calls. If that
// boot rejects — either `fetch` itself rejecting (offline, a 404 right after a redeploy) or
// `init_client` rejecting — `ready` is reset back to `null` so the *next* call starts a fresh
// attempt instead of replaying the same rejection forever: without the reset, one failed boot
// would permanently brick every later mount until a hard page reload. A *resolved* boot is
// never reset, so the success path still only ever runs once. The `.catch` below only resets
// the module-level memo — it does not swallow the rejection for the caller, who still receives
// it via the `ready` promise returned below.
//
// Note: `perspective.init_server` (from `@perspective-dev/client`) returns `void`, not a
// promise — it only stashes whatever is passed to it. Awaiting the two `fetch()` calls
// ourselves (rather than handing `init_server`/`init_client` the in-flight fetch promises
// directly, as `Promise.all([init_server(fetch(...)), init_client(fetch(...))])` would) is
// what lets a rejected `fetch(SERVER_WASM)` actually reach this `attempt` and trigger the
// retry-on-rejection reset below, instead of surfacing later as an unhandled rejection when
// `worker()` awaits the stashed promise.
let ready: Promise<typeof perspective> | null = null;

export const initPerspective = (): Promise<typeof perspective> => {
  if (!ready) {
    const attempt: Promise<typeof perspective> = (async () => {
      const [serverWasm, clientWasm] = await Promise.all([fetch(SERVER_WASM), fetch(CLIENT_WASM)]);
      perspective.init_server(serverWasm);
      await perspective_viewer.init_client(clientWasm);
      return perspective;
    })();
    attempt.catch(() => {
      // Only clear the memo if nothing has raced in a newer attempt already (can't happen
      // in practice — a new attempt is only created when `ready` is falsy — but guards
      // against clobbering a fresher attempt if this ever changes).
      if (ready === attempt) {
        ready = null;
      }
    });
    ready = attempt;
  }
  return ready;
};

type PerspectiveClient = Awaited<ReturnType<typeof perspective.worker>>;

// `perspective.worker()` constructs a brand-new Web Worker (+ its own WASM server
// instance) on *every* call — confirmed in
// `@perspective-dev/client/dist/esm/perspective.js`'s `worker()`/`pe()` helpers, which
// always `new Worker(...)`. Only `Client.terminate()`
// (`@perspective-dev/client/dist/wasm/perspective-js.d.ts`'s `Client.terminate()`) runs the
// close callback that actually calls `Worker.terminate()`. Memoizing the client here —
// instead of every `ExtractionsGrid` mount calling `perspective.worker()` for itself — means
// exactly one worker/WASM heap is ever live for the app's session, no matter how many times
// `/extractions` is mounted and unmounted. Mirrors `ready`'s retry-on-rejection behavior for
// the same reason: a transient worker-boot failure must not brick every later mount.
let clientReady: Promise<PerspectiveClient> | null = null;

export const initPerspectiveClient = (): Promise<PerspectiveClient> => {
  if (!clientReady) {
    const attempt = initPerspective().then((p) => p.worker());
    attempt.catch(() => {
      if (clientReady === attempt) {
        clientReady = null;
      }
    });
    clientReady = attempt;
  }
  return clientReady;
};
