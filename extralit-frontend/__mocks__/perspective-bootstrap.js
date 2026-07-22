// Perspective touches WASM + custom elements at import time; specs use this stub
// (same rationale as __mocks__/tabulator-tables.js).
export const initPerspective = async () => ({
  worker: async () => ({
    table: async (data) => ({
      __data: data,
      size: async () => data.length,
      delete: async () => undefined,
    }),
  }),
});
