import { fileURLToPath } from "node:url";
import { defineVitestConfig } from "@nuxt/test-utils/config";

const r = (p: string) => fileURLToPath(new URL(p, import.meta.url));

export default defineVitestConfig({
  resolve: {
    // Mirror the old jest moduleNameMapper so non-Nuxt (happy-dom) specs resolve
    // the same import paths. Longer keys first so "~~"/"@@" win over "~"/"@".
    alias: {
      "~~": r("./"),
      "@@": r("./"),
      "~": r("./"),
      "@": r("./"),
      assets: r("./assets"),
      // tabulator-tables touches the DOM at construction; specs use the stub.
      "tabulator-tables/dist/css/tabulator.min.css": r("./__mocks__/empty.css"),
      "tabulator-tables": r("./__mocks__/tabulator-tables.js"),
    },
  },
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    include: ["**/*.{test,spec}.{ts,js}"],
    exclude: ["e2e/**", "node_modules/**", ".nuxt/**", "dist/**"],
    env: { TZ: "UTC" },
  },
});
