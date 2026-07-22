import perspective from "@perspective-dev/client";
import perspective_viewer from "@perspective-dev/viewer";
import "@perspective-dev/viewer-datagrid";
import SERVER_WASM from "@perspective-dev/server/dist/wasm/perspective-server.wasm?url";
import CLIENT_WASM from "@perspective-dev/viewer/dist/wasm/perspective-viewer.wasm?url";

// SPA (ssr: false): this runs client-side only. Module-level guard so the WASM
// engines initialize exactly once no matter how often the page remounts (spec §3.3).
let ready: Promise<typeof perspective> | null = null;

export const initPerspective = () => {
  ready ??= Promise.all([
    perspective.init_server(fetch(SERVER_WASM)),
    perspective_viewer.init_client(fetch(CLIENT_WASM)),
  ]).then(() => perspective);
  return ready;
};
