import { fileURLToPath } from "node:url";
import { defineNuxtConfig } from "nuxt/config";
import svgLoader from "vite-svg-loader";
import pkg from "./package.json";

const BASE_URL = process.env.API_BASE_URL ?? "http://0.0.0.0:6900";

export default defineNuxtConfig({
  ssr: false,
  telemetry: false,
  srcDir: ".",

  app: {
    baseURL: process.env.BASE_URL ?? "/",
    head: {
      title: "Extralit",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1" },
        { name: "description", content: "" },
      ],
      link: [
        { rel: "icon", type: "image/x-icon", href: "favicon.ico" },
        { rel: "apple-touch-icon", sizes: "180x180", href: "apple-touch-icon.png" },
        { rel: "icon", sizes: "32x32", href: "favicon-32x32.png" },
        { rel: "icon", sizes: "16x16", href: "favicon-16x16.png" },
        { rel: "manifest", href: "site.webmanifest" },
      ],
    },
  },

  css: ["~/assets/styles.scss"],

  components: [{ path: "~/components", pathPrefix: false, ignore: ["**/types.ts", "**/*.test.*", "**/*.spec.*"] }],

  modules: ["@pinia/nuxt", "@nuxtjs/i18n"],

  i18n: {
    // Locale files live in ./translation/*.js (kept from the Nuxt 2 layout).
    // restructureDir "." disables the v9+ default of nesting under ./i18n/.
    restructureDir: ".",
    langDir: "translation",
    locales: [
      { code: "en", name: "English", file: "en.js" },
      { code: "de", name: "Deutsch", file: "de.js" },
      { code: "es", name: "Español", file: "es.js" },
      { code: "ja", name: "日本語", file: "ja.js" },
    ],
    detectBrowserLanguage: false,
    // (v10 removed the `lazy` option; lazy loading is the default with file-based locales.)
    defaultLocale: "en",
    strategy: "no_prefix",
    // Some translation messages intentionally contain HTML (e.g. doc links);
    // allow them instead of failing the message compiler.
    compilation: { strictMessage: false, escapeHtml: false },
    vueI18n: "./i18n.config.ts",
  },

  runtimeConfig: {
    public: {
      clientVersion: pkg.version,
      communityLink:
        "https://join.slack.com/t/extralit/shared_invite/zt-3gw1ah8bl-AiVNrkIVYOL4yVGOxN8WFw",
      documentationSite: "https://docs.extralit.ai/",
      documentationPersistentStorage:
        "https://docs.extralit.ai/latest/getting_started/how-to-configure-argilla-on-huggingface/#persistent-storage",
    },
  },

  nitro: {
    compressPublicAssets: true,
    // Nuxt 4 serves `public/`, but this app keeps its assets in `static/` (Nuxt 2
    // layout). Serve them at the site root so /images, /fonts, favicons resolve.
    publicAssets: [{ dir: fileURLToPath(new URL("./static", import.meta.url)), baseURL: "/" }],
    devProxy: {
      "/api/": { target: BASE_URL, changeOrigin: true },
      "/share-your-progress": { target: BASE_URL, changeOrigin: true },
    },
  },

  vite: {
    plugins: [svgLoader()],
    // Allow reaching the dev server by arbitrary hostnames (e.g. a containerised
    // browser on the same Docker network). Dev-only; the prod build is a static SPA.
    server: { allowedHosts: true },
    // Pre-bundle deps that are only reached lazily from the home/markdown views.
    // Without this, Vite discovers them at runtime on first navigation and forces
    // a re-optimize + full page reload, which flakes open tabs and the e2e suite.
    optimizeDeps: {
      include: [
        "marked",
        "marked-highlight",
        "marked-katex-extension",
        "highlight.js",
        "dompurify",
      ],
    },
    css: {
      preprocessorOptions: {
        scss: {
          additionalData: '@use "abstract" as *;',
          loadPaths: [fileURLToPath(new URL("./assets/scss", import.meta.url))],
        },
      },
    },
  },

  build: { transpile: ["tabulator-tables"] },

  hooks: {
    "pages:extend"(pages) {
      // Strip co-located non-page files (useXViewModel.ts, *.spec.js) that Nuxt's
      // file router would otherwise register as routes. Deliberate decision: this
      // project's domain-driven layout co-locates a page's view-model and spec next
      // to its .vue under pages/, so we filter the route table rather than relocate
      // the files into composables/ — co-location is the intended structure, not debt.
      function filterNonVue(list: typeof pages) {
        for (let i = list.length - 1; i >= 0; i--) {
          const page = list[i];
          if (page.file && !page.file.endsWith(".vue")) {
            list.splice(i, 1);
          } else if (page.children?.length) {
            filterNonVue(page.children);
          }
        }
      }
      filterNonVue(pages);
    },
  },
});
