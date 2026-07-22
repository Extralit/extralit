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
// boot rejects (a transient `fetch(SERVER_WASM)` blip — offline, or a 404 right after a
// redeploy), `ready` is reset back to `null` so the *next* call starts a fresh attempt
// instead of replaying the same rejection forever: without the reset, one failed boot would
// permanently brick every later mount until a hard page reload. A *resolved* boot is never
// reset, so the success path still only ever runs once. The `.catch` below only resets the
// module-level memo — it does not swallow the rejection for the caller, who still receives
// it via the `ready` promise returned below.
let ready: Promise<typeof perspective> | null = null;

export const initPerspective = (): Promise<typeof perspective> => {
  if (!ready) {
    const attempt: Promise<typeof perspective> = Promise.all([
      perspective.init_server(fetch(SERVER_WASM)),
      perspective_viewer.init_client(fetch(CLIENT_WASM)),
    ]).then(() => perspective);
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
