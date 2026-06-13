# Vue 2 → Vue 3 / Nuxt 2 → Nuxt 4 Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `extralit-frontend` from Vue 2.7 / Nuxt 2.18 (webpack) to Vue 3.5 / Nuxt 4 (Vite), retaining all functionality, gated by Playwright-on-Chromium and a ported Vitest unit suite.

**Architecture:** The domain/use-case layer (`v1/domain`, `v1/infrastructure` with ts-injecty DI) is framework-agnostic and its interfaces stay frozen. Only the Nuxt/Vue-touching *adapters* are swapped: HTTP (`@nuxtjs/axios` → plain axios in a plugin, re-injected into the same DI), Auth (`@nuxtjs/auth-next` → small Pinia-backed `AuthService` implementing `IAuthService`; OIDC stays in extralit-server), Icons (`vue-svgicon` → custom `<svg-icon>` keeping the call signature). Everything else is mechanical Vue-3 codemods + config translation. Straight cutover on `feat/vue-v2-to-v3`.

**Tech Stack:** Nuxt 4.x, Vue 3.5.x, Vite 6, Pinia 2.3/@pinia/nuxt 0.9, @nuxtjs/i18n 9, Vitest 4 + @nuxt/test-utils 4 + @vue/test-utils 2, @vueuse/core 11, mitt, ts-injecty (kept), Playwright (chromium gate).

**Reference spec:** `docs/superpowers/specs/2026-06-13-vue2-to-vue3-migration-design.md`

**Working dir for all commands:** `extralit-frontend/` unless stated otherwise.

---

## Conventions for the implementing engineer

- This is a **cutover**: the app will not build between Phase 1 and the end of Phase 4. That is expected. Commit at each task boundary anyway — commits are the bisection points.
- **Do not** touch `v1/domain/**` use-case logic or `v1/infrastructure/repositories/*Repository.ts` request code. Their constructors take an injected axios and call `this.axios.get/post/...`; that contract is preserved by the new axios plugin. If a repo fails to compile only because of the `@nuxtjs/axios` *type import*, fix the import (Task 12), nothing else.
- Pin exact versions at install time with `npm view <pkg> version`; record the resolved versions in the commit message for Task 2.
- After each phase that can run, run the relevant gate (`npm run dev` boot, `npx playwright test --project=chromium`, `npx vitest run`).

---

## File Structure (what gets created / replaced)

**Created:**
- `vitest.config.ts` — Vitest config (replaces `jest.config.js`)
- `test/setup.ts` — Vitest global setup (replaces `jest.setup.ts` role)
- `plugins/axios.ts` — single Nuxt-4 plugin: builds the axios instance, error handler, cache, DI load
- `v1/infrastructure/services/AuthService.ts` — `implements IAuthService`, Pinia/cookie token store
- `plugins/auth.ts` — instantiates AuthService, provides it to Nuxt + DI
- `components/base/BaseSvgIcon.vue` (+ `plugins/svg-icon.ts`) — custom `<svg-icon>` replacement
- `v1/infrastructure/services/format-number.ts` — exported helpers (replaces `Vue.filter`)
- `components/base/base-toast/bus.ts` — `mitt` event bus (replaces `bus.js`)
- `middleware/route-guard.global.ts`, `middleware/me.global.ts` — Nuxt-4 global middleware (replace `router.middleware`)

**Replaced in place:**
- `package.json`, `nuxt.config.ts`, `tsconfig.json`
- `plugins/directives/click-outside.directive.ts`, `plugins/directives/svg-icon.element.ts`, `plugins/directives/tooltip.directive.ts`
- `v1/infrastructure/services/useAxiosExtension.ts`, `v1/infrastructure/repositories/AxiosErrorHandler.ts`
- `v1/di/di.ts` (the `useAuth`/`useAxios` wiring lines only)
- `v1/domain/services/IAuthService.ts` (drop the `@nuxtjs/auth-next` type import)

**Deleted:**
- `jest.config.js`, `jest.setup.ts`, `babel.config.js`, `plugins/index.ts`, `plugins/di/di.ts`, `plugins/axios/axios-cache.ts`, `plugins/axios/axios-global-handler.ts`

---

## Phase 0 — Baseline & safety net

### Task 1: Capture the green baseline

**Files:** none (read-only)

- [ ] **Step 1: Record current test + lint state**

Run and save output to `docs/superpowers/plans/.baseline.txt` (gitignored scratch — do not commit):
```bash
npm ci
npm run test 2>&1 | tail -40
npx playwright test --project=chromium 2>&1 | tail -30
npm run lint 2>&1 | tail -20
```
Expected: note which specs/e2e currently pass. This is the parity target. If something is already red on `develop`, it is **not** your job to fix it — record it so you don't chase a pre-existing failure later.

- [ ] **Step 2: Confirm dead-dependency claims**

```bash
grep -rln "from \"vuex\"\|from 'vuex'\|@vuex-orm\|vue-vega\|nuxt-mq\|\\$mq\b" \
  --include='*.vue' --include='*.ts' --include='*.js' \
  components pages plugins layouts middleware v1 2>/dev/null
```
Expected: **no output**. If any file prints, add a note to Task 3 to migrate it before deleting the dep. (Spec §9 open item.)

- [ ] **Step 3: Commit a marker (optional)**

No code change; proceed.

---

## Phase 1 — Dependencies & configuration (app will stop building after this)

### Task 2: Rewrite `package.json`

**Files:** Modify `package.json`

- [ ] **Step 1: Resolve target versions**

```bash
for p in nuxt vue @pinia/nuxt pinia @nuxtjs/i18n vitest @nuxt/test-utils @vue/test-utils @vueuse/core mitt vuedraggable @tiptap/vue-3 happy-dom unplugin-vue-markdown vite-svg-loader; do
  printf "%s: " "$p"; npm view "$p" version 2>/dev/null || echo "MISSING"; done
```
Record the printed versions; use them as the pinned `^x.y.z` below.

- [ ] **Step 2: Apply dependency changes**

Remove: `@nuxtjs/composition-api`, `@nuxtjs/axios`, `@nuxtjs/auth-next`, `@nuxtjs/style-resources`, `nuxt-compress`, `nuxt-highlightjs`, `nuxt-mq`, `vue-vega`, `vue-svgicon`, `v-click-outside`, `@nuxt/typescript-build`, `@nuxt/types`, `vue-template-compiler`, `vue-demi`, `vuex`, `@vuex-orm/core`, `@vuex-orm/plugin-axios`, `frontmatter-markdown-loader`, `@tiptap/vue-2`, `nuxt` (v2), `vue` (v2), and the Jest stack: `@vue/vue2-jest`, `vue-jest`, `jest`, `jest-environment-jsdom`, `jest-serializer-vue`, `jest-transform-stub`, `babel-jest`, `babel-core`, all `@babel/*`, `@babel/eslint-parser`, `sass-loader`, `postcss-loader`, `postcss-import`.

Add (deps): `nuxt@^4`, `vue@^3.5`, `@pinia/nuxt@^0.9`, `pinia@^2.3`, `@nuxtjs/i18n@^9`, `@vueuse/core@^11`, `mitt@^3`, `vuedraggable@^4` (the Vue-3 line, pkg name `vuedraggable`), `@tiptap/vue-3@^2.4`, `highlight.js@^11`.
Add (devDeps): `vitest@^4`, `@nuxt/test-utils@^4`, `@vue/test-utils@^2`, `happy-dom@latest`, `vite-svg-loader@latest`, `@nuxt/eslint-config@latest` (replaces `@nuxtjs/eslint-config-typescript`). (`marked` is already a dep and replaces `frontmatter-markdown-loader` — see Task 16 Step 5; no markdown Vite plugin needed since there is exactly one `.md` consumer.)

Keep unchanged: `axios`, `pinia`, `@codescouts/events`, `@jonnytran/vue-pdf-viewer` (verify Vue-3 support in Task 16; flag if not), tiptap extensions/`@tiptap/pm`, `tabulator-tables`, `interactjs`, `ts-injecty`, `luxon`, `marked*`, `papaparse`, `dompurify`, `sass`, `@playwright/test`, eslint/prettier core.

- [ ] **Step 3: Update `scripts`**

Replace `"dev": "nuxt"` → `"dev": "nuxi dev"`, `"build": "nuxi build"`, `"generate": "nuxi generate"`, `"start": "nuxi preview"`. Replace test scripts:
```json
"test": "vitest run",
"test:watch": "vitest",
"test:coverage": "vitest run --coverage",
```
Keep `e2e*`, `lint`, `format*`, `generate-icons` (revisit `generate-icons` in Task 14).

- [ ] **Step 4: Install**

```bash
rm -rf node_modules package-lock.json && npm install
```
Expected: resolves without peer-dep ERESOLVE. If `@jonnytran/vue-pdf-viewer` or another pinned lib hard-blocks on `vue@2`, STOP and flag — do not `--force` silently.

- [ ] **Step 5: Commit**
```bash
git add package.json package-lock.json
git commit -m "build: swap dependency set for Vue 3 / Nuxt 4 (pinned: <versions>)"
```

### Task 3: Delete confirmed-dead Vuex/unused source (if any surfaced in Task 1.2)

**Files:** as surfaced. If Task 1.2 printed nothing, skip and note "no dead source".

- [ ] **Step 1:** Remove the unreferenced files, run `grep` again to confirm zero references, commit `chore: remove unused vuex/vue-vega/nuxt-mq source`.

### Task 4: Rewrite `nuxt.config.ts` for Nuxt 4

**Files:** Modify `nuxt.config.ts`

- [ ] **Step 1: Write the Nuxt-4 config**

Translate the existing config (preserve every behavior in spec §5). Replace the whole file with:
```ts
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
        { hid: "description", name: "description", content: "" },
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

  components: [{ path: "~/components", pathPrefix: false }],

  modules: ["@pinia/nuxt", "@nuxtjs/i18n"],

  i18n: {
    locales: [
      { code: "en", name: "English", file: "en.js" },
      { code: "de", name: "Deutsch", file: "de.js" },
      { code: "es", name: "Español", file: "es.js" },
      { code: "ja", name: "日本語", file: "ja.js" },
    ],
    detectBrowserLanguage: false,
    lazy: true,
    langDir: "translation",
    defaultLocale: "en",
    strategy: "no_prefix",
    bundle: { optimizeTranslationDirective: false },
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
    devProxy: {
      "/api/": { target: BASE_URL, changeOrigin: true },
      "/share-your-progress": { target: BASE_URL, changeOrigin: true },
    },
  },

  vite: {
    plugins: [svgLoader()],
    css: {
      preprocessorOptions: {
        scss: { additionalData: '@use "~/assets/scss/abstract.scss" as *;' },
      },
    },
  },

  build: { transpile: ["pdfjs-dist", "tabulator-tables"] },
});
```
Notes: `@nuxtjs/style-resources` → `vite.css.preprocessorOptions` (verify `assets/scss/abstract.scss` is `@use`-safe; if it has bare top-level statements, wrap as a partial). `nuxt-compress` → `nitro.compressPublicAssets`. `axios.proxy` → `nitro.devProxy`. `router.middleware` → global middleware files (Task 11). `publicRuntimeConfig` → `runtimeConfig.public`. The webpack `extend` md/tabulator babel rules are gone (Vite + esbuild handle them).

- [ ] **Step 2: Create `i18n.config.ts`** (referenced above)
```ts
export default {
  legacy: false,
  fallbackLocale: "en",
};
```

- [ ] **Step 3: Commit** `git add nuxt.config.ts i18n.config.ts && git commit -m "config: port nuxt.config to Nuxt 4 (vite, nitro proxy, i18n v9)"`

### Task 5: Update `tsconfig.json` and remove Babel/Jest config

**Files:** Modify `tsconfig.json`; Delete `babel.config.js`, `jest.config.js`, `jest.setup.ts`

- [ ] **Step 1:** Replace `tsconfig.json` with Nuxt-4 extends:
```json
{
  "extends": "./.nuxt/tsconfig.json"
}
```
(Run `npx nuxi prepare` once after Task 4 to generate `.nuxt/tsconfig.json`. If the project relies on path aliases `@/` and `~/`, Nuxt 4 provides them automatically; verify after prepare.)

- [ ] **Step 2:** `git rm babel.config.js jest.config.js jest.setup.ts`

- [ ] **Step 3: Commit** `git commit -m "config: drop babel/jest config, extend Nuxt 4 tsconfig"`

---

## Phase 2 — Infrastructure adapters (TDD where new code is written)

### Task 6: `format-number` helpers (replaces `Vue.filter`)

**Files:** Create `v1/infrastructure/services/format-number.ts`, `v1/infrastructure/services/format-number.test.ts`; Delete `plugins/extensions/format-number.ts`; Modify `components/features/home/dataset-total/DatasetTotal.vue`

- [ ] **Step 1: Write failing test** `v1/infrastructure/services/format-number.test.ts`
```ts
import { describe, it, expect } from "vitest";
import { formatNumber, formatNumberToK } from "./format-number";

describe("format-number", () => {
  it("formats plain numbers with locale grouping", () => {
    expect(formatNumber(1000)).toBe("1,000");
  });
  it("formats large numbers to K with fraction digits", () => {
    expect(formatNumberToK(12000, 2)).toBe("12k");
    expect(formatNumberToK(1500, 1)).toBe("1.5k");
  });
});
```
(Match the exact output of the current `plugins/extensions/format-number.ts` — open it and copy the `Intl.NumberFormat`/`notation: "compact"` logic verbatim into the helpers so behavior is identical. Adjust the expected strings in this test to the real current output before running.)

- [ ] **Step 2: Run, expect FAIL** `npx vitest run v1/infrastructure/services/format-number.test.ts` → fails (module not found). (Vitest config lands in Task 18; if it doesn't exist yet, write Task 18 first or run with `npx vitest run --config ./vitest.config.ts` after Task 18. Recommended order: do Task 18 before Task 6’s Step 2.)

- [ ] **Step 3: Implement** `v1/infrastructure/services/format-number.ts` — export `formatNumber(value)` and `formatNumberToK(number, maximumFractionDigits)` using the same `Intl.NumberFormat` settings the old filters used.

- [ ] **Step 4: Run, expect PASS.**

- [ ] **Step 5: Update the one consumer.** In `DatasetTotal.vue`: remove `{{ total | formatNumberToK(2) }}`, import `formatNumberToK` and render `{{ formatNumberToK(total, 2) }}`. Delete `plugins/extensions/format-number.ts`.

- [ ] **Step 6: Commit** `git commit -m "refactor: replace Vue.filter number formatters with helpers"`

### Task 7: `mitt` event bus (replaces `new Vue()` bus)

**Files:** Create `components/base/base-toast/bus.ts`, `components/base/base-toast/bus.test.ts`; Delete `components/base/base-toast/bus.js`

- [ ] **Step 1: Failing test**
```ts
import { describe, it, expect, vi } from "vitest";
import bus from "./bus";
describe("toast bus", () => {
  it("emits and receives events", () => {
    const handler = vi.fn();
    bus.on("show", handler);
    bus.emit("show", { message: "hi" });
    expect(handler).toHaveBeenCalledWith({ message: "hi" });
  });
});
```
- [ ] **Step 2: Run, expect FAIL.**
- [ ] **Step 3: Implement** `bus.ts`:
```ts
import mitt from "mitt";
export default mitt();
```
- [ ] **Step 4: Update consumers.** `grep -rln "base-toast/bus" components` → for each, replace `bus.$emit(...)` → `bus.emit(...)`, `bus.$on(...)` → `bus.on(...)`, `bus.$off(...)` → `bus.off(...)`. Delete `bus.js`.
- [ ] **Step 5: Run test, expect PASS. Commit** `git commit -m "refactor: replace Vue-instance toast bus with mitt"`

### Task 8: Tooltip directive (replaces `new Vue()` mount)

**Files:** Modify `plugins/directives/tooltip.directive.ts`

- [ ] **Step 1:** Read the current file. It does `new Vue({ render: ... }).$mount()` to create a tooltip element. Rewrite using Vue 3:
```ts
import { createApp, h } from "vue";
// ...inside the directive's mount logic:
const app = createApp({ render: () => h(/* same tooltip vnode */) });
const mountPoint = document.createElement("div");
app.mount(mountPoint);
// use mountPoint.firstElementChild as the tooltip node; app.unmount() on cleanup
```
Preserve the directive's existing positioning/show/hide behavior exactly; only the instance-creation mechanism changes. Convert the Vue-2 directive hooks (`bind`/`unbind`/`update`) to Vue-3 (`mounted`/`unmounted`/`updated`).

- [ ] **Step 2:** Manual smoke is deferred to Playwright (Task 17). Commit `git commit -m "refactor: port tooltip directive to Vue 3 createApp"`

### Task 9: click-outside directive → `@vueuse/core`

**Files:** Modify `plugins/directives/click-outside.directive.ts`

- [ ] **Step 1:** Replace the `Vue.use(ClickOutside)` global-plugin file with a Nuxt-4 directive registration that preserves the `v-click-outside` directive name used by 18 consumers:
```ts
import { onClickOutside } from "@vueuse/core";
import { defineNuxtPlugin } from "#app";

export default defineNuxtPlugin((nuxtApp) => {
  const stops = new WeakMap<HTMLElement, () => void>();
  nuxtApp.vueApp.directive("click-outside", {
    mounted(el, binding) {
      const handler = typeof binding.value === "function" ? binding.value : binding.value?.handler;
      if (handler) stops.set(el, onClickOutside(el, (e) => handler(e)));
    },
    unmounted(el) {
      stops.get(el)?.();
      stops.delete(el);
    },
  });
});
```
Move this file to `plugins/click-outside.ts` (Nuxt 4 auto-registers `plugins/*.ts`; the nested `plugins/directives/` dir is no longer auto-scanned the same way — see Task 11 for the plugin-loading change). Verify the 18 consumers use `v-click-outside="fn"` or `v-click-outside="{ handler }"`; support both as above.

- [ ] **Step 2: Commit** `git commit -m "refactor: reimplement v-click-outside via @vueuse/core"`

### Task 10: Custom `<svg-icon>` (replaces `vue-svgicon`)

**Files:** Create `components/base/BaseSvgIcon.vue`, `plugins/svg-icon.ts`, `components/base/BaseSvgIcon.test.ts`; Delete `plugins/directives/svg-icon.element.ts`

- [ ] **Step 1:** Inspect current usage shape: `grep -rho "<svgicon[^>]*" components pages | head`. Capture the props actually used (typically `name`, `width`, `height`, `color`). The new component must accept the same props.

- [ ] **Step 2: Failing test** `BaseSvgIcon.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BaseSvgIcon from "./BaseSvgIcon.vue";
describe("BaseSvgIcon", () => {
  it("renders an svg with the icon name as data attribute", () => {
    const w = mount(BaseSvgIcon, { props: { name: "check", width: 16, height: 16 } });
    expect(w.find("svg").exists()).toBe(true);
    expect(w.attributes("data-icon")).toBe("check");
  });
});
```
- [ ] **Step 3: Run, expect FAIL.**
- [ ] **Step 4: Implement.** Use `vite-svg-loader` to import raw SVGs from `static/icons` (or `assets/icons`) by name. Simplest robust approach: a Vite glob import.
```vue
<template>
  <span class="svg-icon" :data-icon="name" :style="{ width: sz(width), height: sz(height), color }" v-html="svg" />
</template>
<script setup lang="ts">
import { computed } from "vue";
const props = withDefaults(defineProps<{ name: string; width?: number|string; height?: number|string; color?: string }>(), {});
const modules = import.meta.glob("~/static/icons/**/*.svg", { query: "?raw", import: "default", eager: true }) as Record<string,string>;
const sz = (v?: number|string) => (v == null ? undefined : typeof v === "number" ? `${v}px` : v);
const svg = computed(() => {
  const hit = Object.entries(modules).find(([p]) => p.endsWith(`/${props.name}.svg`));
  return hit ? hit[1] : "";
});
</script>
```
(Confirm the real icon directory path and adjust the glob. If icons live as generated JS components under `assets/icons`, instead point the glob at the source SVGs the generator consumed — those are the durable source of truth.)
- [ ] **Step 5: Register globally** in `plugins/svg-icon.ts` so the existing `<svgicon .../>` tag resolves. Either (a) register under both names:
```ts
import { defineNuxtPlugin } from "#app";
import BaseSvgIcon from "~/components/base/BaseSvgIcon.vue";
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component("svgicon", BaseSvgIcon);
  nuxtApp.vueApp.component("SvgIcon", BaseSvgIcon);
});
```
This keeps all 79 `<svgicon>` call sites unchanged. Delete `plugins/directives/svg-icon.element.ts`.
- [ ] **Step 6: Run test, expect PASS. Commit** `git commit -m "feat: custom svg-icon component replacing vue-svgicon"`

### Task 11: Plugin loader + global middleware → Nuxt 4

**Files:** Delete `plugins/index.ts`, `plugins/di/di.ts`, `plugins/axios/axios-cache.ts`, `plugins/axios/axios-global-handler.ts`; Create `middleware/route-guard.global.ts`, `middleware/me.global.ts`; Modify the remaining `plugins/*` to Nuxt-4 `defineNuxtPlugin` shape

- [ ] **Step 1:** Nuxt 4 auto-imports every `plugins/*.ts`. The old `plugins/index.ts` manual `require.context` loader is obsolete — delete it. Each former sub-plugin becomes its own `plugins/<name>.ts` exporting `defineNuxtPlugin(...)`. Convert: `plugins/language/*`, `plugins/logo/*`, `plugins/extensions/*` (non-filter ones), `plugins/directives/*` (badge, circle, required-field, tooltip, copy-code) — each registers its directive via `nuxtApp.vueApp.directive(...)`. The old signature `export default (context, inject) => {}` becomes `export default defineNuxtPlugin((nuxtApp) => {})`; `inject("x", v)` becomes `nuxtApp.provide("x", v)`.

- [ ] **Step 2:** Convert `router.middleware: ["route-guard","me"]` to global middleware. Move `middleware/route-guard.ts` → `middleware/route-guard.global.ts` and `middleware/me.ts` → `middleware/me.global.ts`. Rewrite their Nuxt-2 signature `export default ({ $auth, redirect, route }) => {}` to Nuxt-4:
```ts
export default defineNuxtRouteMiddleware((to) => {
  const { $auth } = useNuxtApp(); // AuthService, provided in Task 13
  if (!$auth.loggedIn && /* needs auth */) return navigateTo("/sign-in");
  // ...preserve exact original redirect logic, mapping redirect("/") -> navigateTo("/")
});
```
Keep the original conditional logic byte-for-byte; only the framework calls change (`redirect(x)`→`navigateTo(x)`, `$auth`→`useNuxtApp().$auth`).

- [ ] **Step 3: Commit** `git commit -m "refactor: Nuxt 4 plugin + global middleware structure"`

### Task 12: Axios plugin + error handler + cache (replaces `@nuxtjs/axios`)

**Files:** Create `plugins/2.axios.ts`; Modify `v1/infrastructure/repositories/AxiosErrorHandler.ts`, `v1/infrastructure/services/useAxiosExtension.ts`; the `NuxtAxiosInstance` type import in ~20 repo files

- [ ] **Step 1: Rewrite `AxiosErrorHandler.ts`** to use a standard axios response interceptor instead of auth-next's `$axios.onError`:
```ts
import type { AxiosInstance } from "axios";
import { useNotifications } from "../services";

export const loadErrorHandler = (axios: AxiosInstance, t: (k: string) => string) => {
  const notification = useNotifications();
  axios.interceptors.response.use(
    (r) => r,
    (error) => {
      const { status, data } = error.response ?? {};
      notification.clear();
      // ...identical priority logic as the current file (businessLogic → detail → http status),
      // calling t(key) and notification.notify(...). Re-throw error at the end.
      return Promise.reject(error);
    }
  );
};
```
Preserve the three-tier message-priority logic verbatim. Note the signature change: it now takes `(axios, t)` instead of a Nuxt `context` (the plugin supplies `t` via i18n).

- [ ] **Step 2: Rewrite `useAxiosExtension.ts`.** Replace `NuxtAxiosInstance` with a plain axios instance + `makePublic`:
```ts
import axios, { type AxiosInstance } from "axios";
import { loadCache } from "../repositories/AxiosCache";
import { loadErrorHandler } from "../repositories/AxiosErrorHandler";

export interface PublicAxiosInstance extends AxiosInstance {
  makePublic: (config?: { enableErrors: boolean }) => AxiosInstance;
}

export const useAxiosExtension = (base: AxiosInstance, t: (k: string) => string) => {
  const makePublic = (config = { enableErrors: true }) => {
    const pub = axios.create({ baseURL: base.defaults.baseURL, withCredentials: false, headers: { Authorization: undefined } });
    if (config.enableErrors) loadErrorHandler(pub, t);
    loadCache(pub);
    return pub;
  };
  const create = () => Object.assign(base, { makePublic }) as PublicAxiosInstance;
  return create;
};
```
(Keep the public-name `PublicNuxtAxiosInstance` as a type alias re-export if other files import it, to avoid churn: `export type PublicNuxtAxiosInstance = PublicAxiosInstance;`.)

- [ ] **Step 3: Create `plugins/2.axios.ts`** — the single composition root for HTTP + DI:
```ts
import axios from "axios";
import { defineNuxtPlugin, useRuntimeConfig } from "#app";
import { useAxiosExtension } from "~/v1/infrastructure/services/useAxiosExtension";
import { loadCache } from "~/v1/infrastructure/repositories/AxiosCache";
import { loadErrorHandler } from "~/v1/infrastructure/repositories/AxiosErrorHandler";

export default defineNuxtPlugin((nuxtApp) => {
  const { $i18n } = nuxtApp as any;
  const t = (k: string) => String($i18n.t(k));

  const instance = axios.create({ baseURL: "/api" });
  // auth header: read token from AuthService (provided by plugins/auth.ts, ordered before this)
  instance.interceptors.request.use((cfg) => {
    const token = (nuxtApp.$auth as any)?.token;
    if (token) cfg.headers.Authorization = `Bearer ${token}`;
    return cfg;
  });
  loadErrorHandler(instance, t);
  loadCache(instance);

  nuxtApp.provide("axios", instance);
});
```
Ensure plugin ordering: name files so `auth.ts` (Task 13) loads before `axios.ts` and both before `di.ts`. Nuxt 4 orders plugins alphabetically within `plugins/`; use numeric prefixes (`1.auth.ts`, `2.axios.ts`, `3.di.ts`) to lock order.

- [ ] **Step 4: Fix the `NuxtAxiosInstance` type imports** in the ~20 repo files:
```bash
grep -rln "@nuxtjs/axios" v1/infrastructure | xargs sed -i \
  -e 's/import { type NuxtAxiosInstance } from "@nuxtjs\/axios";/import type { AxiosInstance } from "axios";/' \
  -e 's/NuxtAxiosInstance/AxiosInstance/g'
```
Then grep to confirm no `@nuxtjs/axios` references remain. Do **not** change any `this.axios.get/post/...` calls — plain axios shares that API.

- [ ] **Step 5: Commit** `git commit -m "feat: plain-axios HTTP plugin with ported error handler + cache"`

### Task 13: `AuthService` (replaces `@nuxtjs/auth-next`)

**Files:** Create `v1/infrastructure/services/AuthService.ts`, `v1/infrastructure/services/AuthService.test.ts`, `plugins/1.auth.ts`; Modify `v1/domain/services/IAuthService.ts`, `v1/di/di.ts`

- [ ] **Step 1: Drop the auth-next type from the interface.** In `IAuthService.ts`, replace `import { HTTPResponse } from "@nuxtjs/auth-next";` and change `setUserToken(token: string): Promise<void | HTTPResponse>;` → `setUserToken(token: string): Promise<void>;`. Keep all other members (`loggedIn`, `user`, `logout`, `setUser`).

- [ ] **Step 2: Failing test** `AuthService.test.ts`:
```ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { AuthService } from "./AuthService";

describe("AuthService", () => {
  let store: Record<string, string>;
  beforeEach(() => { store = {}; });
  const fakeCookie = (k: string) => ({ get value() { return store[k]; }, set value(v) { store[k] = v; } });

  it("is logged out with no token", () => {
    const a = new AuthService(fakeCookie("t") as any);
    expect(a.loggedIn).toBe(false);
  });
  it("becomes logged in after setUserToken", async () => {
    const a = new AuthService(fakeCookie("t") as any);
    await a.setUserToken("ABC");
    expect(a.loggedIn).toBe(true);
    expect(a.token).toBe("ABC");
  });
  it("clears token and user on logout", async () => {
    const a = new AuthService(fakeCookie("t") as any);
    await a.setUserToken("ABC");
    a.setUser({ id: 1 });
    await a.logout();
    expect(a.loggedIn).toBe(false);
    expect(a.user).toBeNull();
  });
});
```
- [ ] **Step 3: Run, expect FAIL.**
- [ ] **Step 4: Implement** `AuthService.ts` — a class taking a token-ref (Nuxt `useCookie` ref injected at plugin time, so the class stays unit-testable):
```ts
import type { Ref } from "vue";
import type { IAuthService } from "~/v1/domain/services/IAuthService";

export class AuthService implements IAuthService {
  private _user: Record<string, unknown> | null = null;
  constructor(private readonly tokenRef: Ref<string | null | undefined>) {}
  get token() { return this.tokenRef.value ?? null; }
  get loggedIn() { return !!this.tokenRef.value; }
  get user() { return this._user; }
  setUser(user: unknown) { this._user = (user as Record<string, unknown>) ?? null; }
  async setUserToken(token: string) { this.tokenRef.value = token; }
  async logout() { this.tokenRef.value = null; this._user = null; }
}
```
- [ ] **Step 5: Run, expect PASS.**
- [ ] **Step 6: Create `plugins/1.auth.ts`:**
```ts
import { defineNuxtPlugin, useCookie } from "#app";
import { AuthService } from "~/v1/infrastructure/services/AuthService";
export default defineNuxtPlugin((nuxtApp) => {
  const token = useCookie<string | null>("auth_token", { sameSite: "lax" });
  nuxtApp.provide("auth", new AuthService(token));
});
```
- [ ] **Step 7: Rewire DI** in `v1/di/di.ts`: change `const useAuth = () => context.$auth;` → accept the provided service. Since `loadDependencyContainer` currently takes a Nuxt-2 `context`, update its signature to take `nuxtApp` and read `nuxtApp.$auth` / `nuxtApp.$axios`. Replace `const useAxios = useAxiosExtension(context)` with `const useAxios = useAxiosExtension(nuxtApp.$axios, t)`. Create `plugins/3.di.ts` that calls `loadDependencyContainer(useNuxtApp())`. (The old `plugins/di/di.ts` is deleted in Task 11.)

- [ ] **Step 8: Commit** `git commit -m "feat: custom AuthService token store implementing IAuthService"`

---

## Phase 3 — Mechanical Vue 3 codemods

### Task 14: Composition-API import swaps (48 files)

**Files:** every file importing `@nuxtjs/composition-api`

- [ ] **Step 1:** Map the imports. `ref/computed/watch/onMounted/onBeforeMount/onBeforeUnmount/nextTick/defineComponent` come from `vue`. `useRoute/useRouter` are Nuxt-4 auto-imports (or from `vue-router`). `useContext` → `useNuxtApp`. `useFetch` → Nuxt-4 `useAsyncData`/`useFetch` (semantics differ — see Step 3).

- [ ] **Step 2: Bulk-swap the pure-Vue imports:**
```bash
grep -rln "@nuxtjs/composition-api" components pages v1 layouts | while read f; do
  sed -i 's#from "@nuxtjs/composition-api"#from "vue"#g' "$f"; done
```
Then for each file still importing `useRoute`, `useRouter`, `useContext`, `useFetch` from `vue` (now wrong), hand-fix: remove those names from the `vue` import and rely on Nuxt auto-imports (`useRoute`, `useRouter`, `useNuxtApp`), replacing `useContext()` usages with `useNuxtApp()` and adjusting `.app`/`.$axios`/`.i18n` member access (`ctx.app.i18n` → `nuxtApp.$i18n`).

- [ ] **Step 3: `useFetch` (≈8 files).** Nuxt-2 `useFetch(async () => {...})` ran the body on setup. Replace with `useAsyncData(<uniqueKey>, async () => {...})` or move the call into `onMounted` if it mutates refs imperatively. Convert one file, verify it compiles, then do the rest the same way. Document each converted key.

- [ ] **Step 4:** `grep -rl "@nuxtjs/composition-api" .` → expect zero (outside node_modules). Commit `git commit -m "refactor: migrate composition-api imports to Vue 3 / Nuxt composables"`

### Task 15: `slot`/`slot-scope` → `v-slot` (35 files), `$listeners` → `$attrs` (4 files), filters audit

**Files:** the 35 legacy-slot `.vue` files; `BaseBadge.vue`, `EntityBadge.vue`, `FilterTooltip.vue`, `FilterBadge.vue`

- [ ] **Step 1: Slots.** For each of the 35 files, convert `<template slot="x" slot-scope="p">` → `<template #x="p">` and element-level `slot="x"` → wrap in `<template #x>`. Run `grep -rln 'slot=\|slot-scope' components pages layouts` → must reach zero. (No safe blanket sed; do per-file, they are few.)

- [ ] **Step 2: `$listeners`.** In the 4 files, remove `v-on="$listeners"` (Vue 3 folds listeners into `$attrs`, and `inheritAttrs` defaults pass them through). Where a component sets `inheritAttrs: false` and manually forwards, keep `v-bind="$attrs"` (now includes `onXxx`). Verify each badge/filter component still forwards click/hover.

- [ ] **Step 3: Filter sweep.** `grep -rn "{{[^}]*|[^|}]*}}" components pages | grep -v "||"` → must be zero after Task 6 fixed `DatasetTotal.vue`. If any remain, convert to helper calls.

- [ ] **Step 4: Commit** `git commit -m "refactor: v-slot syntax, $attrs listeners, remove template filters"`

### Task 16: One-off heavy libs

**Files:** the `vuedraggable` file (1), the `@tiptap/vue-2` file (1), `tabulator`/`interactjs` consumers, pdf-viewer usage, `components/features/annotation/shortcuts/AnnotationHelpShortcut.vue` (the sole `.md` consumer)

- [ ] **Step 1: vuedraggable.** Change import to `vuedraggable` v4 (Vue-3). API is compatible; verify the `v-model`/`:list` binding and `@change` still work.

- [ ] **Step 2: tiptap.** In the single file, `@tiptap/vue-2` → `@tiptap/vue-3` (`import { Editor, EditorContent } from "@tiptap/vue-3"`). Extensions packages are version-agnostic; no other change.

- [ ] **Step 3: tabulator-tables / interactjs.** Ensure any module-load access to `window`/`document` is deferred: wrap construction in `onMounted` and, if needed, `const { TabulatorFull } = await import("tabulator-tables")`. `build.transpile` already includes tabulator (Task 4).

- [ ] **Step 4: `@jonnytran/vue-pdf-viewer`.** Confirm it renders under Vue 3 (it was pinned for the Vue-2 app). If it imports `vue@2`, replace with a Vue-3-compatible PDF viewer or load the component client-only. Flag to the user if a swap is needed (this is the one library with real uncertainty).

- [ ] **Step 5: `.md` loader (replaces `frontmatter-markdown-loader`).** `AnnotationHelpShortcut.vue` currently does `require.context("../../../../docs/", false, /^[^_]+\.md$/, "lazy")` then `await folderContent("./shortcuts.md")` to get rendered HTML. Replace the webpack `require.context` with a Vite glob of raw markdown + `marked` (already a dep):
```ts
import { marked } from "marked";
const docs = import.meta.glob("~/docs/*.md", { query: "?raw", import: "default" });
// ...where it loaded shortcuts.md:
const raw = (await docs["/docs/shortcuts.md"]()) as string;
const html = marked.parse(raw);   // assign to the same ref that held folderContent body
```
Confirm the glob key path (`/docs/shortcuts.md`) by logging `Object.keys(docs)` once. Preserve `dompurify` sanitization if the original sanitized before injecting.

- [ ] **Step 6: Commit** `git commit -m "refactor: port draggable, tiptap, tabulator/interactjs, md-loader to Vue 3"`

---

## Phase 4 — Boot & functional gate

### Task 17: Boot the app and drive Playwright-chromium to green

**Files:** as needed to fix runtime errors

- [ ] **Step 1: Prepare + boot.**
```bash
npx nuxi prepare
npm run dev
```
Fix compile/boot errors iteratively. Common ones: stray Nuxt-2 `this.$nuxt`/`this.$axios` in components (replace with `useNuxtApp().$axios`), `process.client` → `import.meta.client`, `$config` → `useRuntimeConfig()`. Work until `http://localhost:3000` renders the sign-in page.

- [ ] **Step 2: Run the e2e suite on chromium only.**
```bash
npx playwright test --project=chromium
```
The suite mocks the backend (`e2e/common/*-api-mock.ts`), so no server is needed.

- [ ] **Step 3: Drive failures to green page-by-page**, in this order (matches `e2e/` dirs): `login-page`, `datasets-page`, `dataset-setting-page`, `annotation-mode-page`, `import-configuration-workflow`, `user-setting-page`. For each failing spec, fix the underlying component/adapter — not the test. If a screenshot baseline differs only by antialiasing within `maxDiffPixelRatio: 0.1`, it passes; if structurally different, fix the component.

- [ ] **Step 4: Full chromium run green.** `npx playwright test --project=chromium` → all pass. Commit `git commit -m "fix: drive Vue 3 app to passing chromium e2e suite"`

---

## Phase 5 — Unit test migration (Vitest)

### Task 18: Vitest config + setup (do this before Task 6 Step 2)

**Files:** Create `vitest.config.ts`, `test/setup.ts`

- [ ] **Step 1: `vitest.config.ts`:**
```ts
import { defineVitestConfig } from "@nuxt/test-utils/config";

export default defineVitestConfig({
  test: {
    environment: "happy-dom",
    globals: true,
    setupFiles: ["./test/setup.ts"],
    include: ["**/*.{test,spec}.{ts,js}"],
    exclude: ["e2e/**", "node_modules/**"],
  },
});
```
- [ ] **Step 2: `test/setup.ts`** — port anything `jest.setup.ts` did (timezone is set via env; replicate global mocks/stubs). Add stubs for `tabulator-tables` (the old `__mocks__/tabulator-tables.js`) via `vi.mock` if specs rely on it.
- [ ] **Step 3: Smoke** `npx vitest run v1/infrastructure/services/format-number.test.ts` → passes (from Task 6). Commit `git commit -m "test: add Vitest + @nuxt/test-utils config"`

### Task 19: Port the 79 Jest specs to Vitest

**Files:** all `*.spec.ts` / `*.test.ts` under `components`, `v1`, `pages`

- [ ] **Step 1: Globals.** With `globals: true`, `describe/it/expect` need no import. Where specs import from `@jest/globals`, change to `vitest`. Replace `jest.fn()` → `vi.fn()`, `jest.mock` → `vi.mock`, `jest.spyOn` → `vi.spyOn` (`grep -rl "jest\." | xargs sed -i 's/\bjest\./vi./g'` then add `import { vi } from "vitest"` where needed, or rely on globals + `vitest/globals` types).

- [ ] **Step 2: `@vue/test-utils` v1→v2 API.** Per file: `propsData:` → `props:`; `wrapper.contains(s)` → `wrapper.find(s).exists()`; `findAll().at(n)` → `findAll()[n]`; `createLocalVue()` + `localVue.use(...)` → `mount(C, { global: { plugins: [...] } })`; `wrapper.emitted("input")` → `wrapper.emitted("update:modelValue")` for migrated v-model components; stubs become opt-in (`global: { stubs: {...} }`).

- [ ] **Step 3: Iterate to green.** `npx vitest run`. Fix file-by-file. For component specs that mount components depending on Nuxt auto-imports, use `mockNuxtImport` from `@nuxt/test-utils/runtime`. Tests asserting `vue-svgicon` internals update to the new `<svg-icon>` (`data-icon`).

- [ ] **Step 4: Full suite green.** `npx vitest run` → all pass (parity with the Task 1 baseline count; if a spec tested a deleted dep, delete that spec and note it in the commit). Commit `git commit -m "test: port unit suite from Jest to Vitest"`

---

## Phase 6 — Cleanup & verification

### Task 20: Lint, typecheck, build, final gate

**Files:** ESLint config if flat-config migration needed

- [ ] **Step 1: ESLint.** Nuxt 4 prefers `@nuxt/eslint`. If the old `.eslintrc` + `@nuxtjs/eslint-config-typescript` fails, migrate to `eslint.config.mjs` via `@nuxt/eslint`. Run `npm run lint` → clean (or only pre-existing-baseline warnings).

- [ ] **Step 2: Typecheck.** `npx nuxi typecheck` → no errors. Fix residual Nuxt-2 type imports (`@nuxt/types`, `@nuxtjs/auth-next`, `@nuxtjs/axios`) — there should be none left; grep to prove it: `grep -rln "@nuxt/types\|@nuxtjs/auth-next\|@nuxtjs/axios\|@nuxtjs/composition-api" --include='*.ts' --include='*.vue' . | grep -v node_modules` → empty.

- [ ] **Step 3: Production build.** `npm run build` → succeeds. Then `npm run generate` if static output is used by deployment (the HF-space bundle).

- [ ] **Step 4: Final acceptance (Definition of Done, spec §8):**
```bash
npx vitest run                       # green
npx playwright test --project=chromium   # green
npm run lint                         # clean
npx nuxi typecheck                   # clean
npm run build                        # succeeds
```
All five green. Commit `git commit -m "chore: lint/type/build clean on Vue 3 / Nuxt 4"`

- [ ] **Step 5: Update docs.** Edit `extralit-frontend/CLAUDE.md`: remove "Vuex → Pinia migration in progress" stale note, update Key Technologies to Nuxt 4 / Vue 3 / Vitest, update test commands (`npm run test` now = Vitest). Commit `git commit -m "docs: update frontend CLAUDE.md for Nuxt 4 stack"`

---

## Definition of Done

- `npx playwright test --project=chromium` — all e2e flows pass (authoritative functional parity).
- `npx vitest run` — unit suite green at baseline parity.
- `npm run lint`, `npx nuxi typecheck`, `npm run build` — clean.
- Zero references to `@nuxtjs/axios`, `@nuxtjs/auth-next`, `@nuxtjs/composition-api`, `@nuxt/types`, `vue-svgicon`, `vuex`, `@vuex-orm/*` in app source.
- `develop` untouched; all work isolated on `feat/vue-v2-to-v3`.

## Risk register (carry into execution)

| Risk | Trigger | Mitigation |
|---|---|---|
| `@jonnytran/vue-pdf-viewer` is Vue-2-only | npm install peer error or runtime crash | Task 16 Step 4 — swap viewer or client-only load; flag to user early |
| `assets/scss/abstract.scss` not `@use`-safe | Vite scss build error in Task 4 | Refactor into a pure partial (vars/mixins only) |
| i18n v9 `useFetch`-style lazy loading change | Locale not switching | Verify `i18n.config.ts` + `langDir`; spot-check all 4 locales in UI |
| `useFetch` semantic change breaks data load | Blank pages in Task 17 | Task 14 Step 3 — convert to `useAsyncData` or `onMounted` per file |
| Plugin ordering (axios before auth before di) | `$auth`/`$axios` undefined at DI load | numeric filename prefixes `1.auth`,`2.axios`,`3.di` |
