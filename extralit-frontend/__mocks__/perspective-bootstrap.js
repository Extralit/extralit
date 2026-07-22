// Perspective touches WASM + custom elements at import time; specs use this stub
// (same rationale as __mocks__/tabulator-tables.js).
const stubClient = {
  table: async (data) => ({
    __data: data,
    size: async () => data.length,
    delete: async () => undefined,
  }),
};

export const initPerspective = async () => ({
  worker: async () => stubClient,
});

// Mirrors the real module's hoisted-client memo (`initPerspectiveClient`): components should
// call this instead of `(await initPerspective()).worker()` so only one stub client exists.
export const initPerspectiveClient = async () => stubClient;
