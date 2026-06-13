# Vue 2 → Vue 3 / Nuxt 2 → Nuxt 4 Migration — Design

**Date:** 2026-06-13
**Component:** `extralit-frontend`
**Branch:** `feat/vue-v2-to-v3`
**Status:** Approved design → implementation planning

## 1. Goal & Constraints

Migrate `extralit-frontend` from Vue 2.7 / Nuxt 2.18 to **Vue 3.5 / Nuxt 4**, retaining
**all current functionality**. The app is a **client-only SPA** (`ssr: false`) — this is
load-bearing and stays true after migration (no new SSR surface to reason about).

Validation gates, in order of authority:
1. **Playwright e2e on Chromium** — the functional source of truth. The suite mocks the
   backend (`e2e/common/*-api-mock.ts`), so it runs without a live server. Every page-level
   flow (login, datasets, dataset-settings, annotation-mode, import-config, user-settings)
   must pass.
2. **Vitest unit suite** — ported from the 79 Jest specs; component/use-case regression net.
3. `npm run lint` + `tsc` typecheck clean.

Non-goals: no feature work, no redesign, no SSR adoption, no Vuex→Pinia work (already done),
no gratuitous refactor beyond what the migration forces.

## 2. Current-State Facts (measured, not assumed)

| Fact | Value | Implication |
|---|---|---|
| `.vue` components | 247 | Bulk of the work is mechanical, not architectural |
| Files importing `@nuxtjs/composition-api` | 48 | Import-path swap to `vue` / Nuxt composables |
| State management | Pinia (`@pinia/nuxt` 0.2.1) | Vuex / `@vuex-orm/*` deps are **dead** — delete them |
| `$store` / `mapActions` / vuex refs | 9 files | Stale leftovers; verify dead, remove |
| Legacy `slot=` / `slot-scope=` | 35 files | Convert to `v-slot` (Vue 2.6+ supports it) |
| Template filters (`\| filter`) | **1** site (`DatasetTotal.vue`) | Trivial — one computed/helper call |
| `Vue.filter` registrations | `format-number.ts` (2 filters) | Convert to importable helpers |
| `$listeners` usage | 4 files | Fold into `$attrs` (Vue 3 merges them) |
| `new Vue()` event bus | `base-toast/bus.js` | Replace with `mitt` |
| `new Vue()` in tooltip directive | `tooltip.directive.ts` | Re-implement with Vue 3 `createApp`/`render` |
| `::v-deep` / `/deep/` | 0 files | Nothing to do |
| `functional:` SFCs | 0 files | Nothing to do |
| HTTP | `@nuxtjs/axios` (`NuxtAxiosInstance`) injected into ~20 repository classes via ts-injecty | Replace with plain axios in a plugin |
| Auth | `@nuxtjs/auth-next`, **all endpoints disabled** — used only as token store + `loggedIn` flag behind `IAuthService`; OIDC handshake is in extralit-server | Replace with small custom AuthService |
| Icons | `vue-svgicon` 3.x, `<svgicon>` used in 79 files, generated from `static/icons` | Custom Vue 3 `<svg-icon>` preserving call signature |
| `v-click-outside` | 18 files, behind custom directive plugin | Swap directive internals → `@vueuse/core onClickOutside` |
| `vuedraggable` 2.x | 1 file | → `vuedraggable@next` (Vue 3) |
| `@tiptap/vue-2` | 1 file | → `@tiptap/vue-3` |
| i18n | `@nuxtjs/i18n` v7 (4 locales, lazy, `no_prefix`) | → v9 (config reshape) |
| Heavy client libs | `tabulator-tables`, `interactjs` | Guard `window`/`document` access in `onMounted` / client-only |
| Unit tests | Jest 29 + `@vue/vue2-jest` + `@vue/test-utils` 1.x, 79 specs | → Vitest 4 + `@vue/test-utils` 2 + `@nuxt/test-utils` 4 |
| e2e | Playwright, backend mocked, 3 browser projects | Keep; **gate on chromium** |

**Why this codebase is low-risk:** already on Pinia, already SPA-only, already 48 files on
Composition API, near-zero filters/deep-selectors/functional components. The genuine breaking
changes total ~45 files, almost all mechanical.

## 3. Target Versions

| Package | From → To |
|---|---|
| `nuxt` | 2.18 → **4.x** (latest stable) |
| `vue` | 2.7.16 → **3.5.x** |
| build | webpack → **Vite** (Nuxt 4 default) |
| `@pinia/nuxt` / `pinia` | 0.2.1 / 2.x → **0.9.x / 2.3.x** |
| `@nuxtjs/i18n` | 7.x → **9.x** |
| test | Jest → **Vitest 4** + `@nuxt/test-utils` 4 + `@vue/test-utils` 2 |
| `@vueuse/core` | (new) → **^11.x** |
| `mitt` | (new) | event bus |

**Removed entirely:** `@nuxtjs/composition-api`, `@nuxtjs/axios`, `@nuxtjs/auth-next`,
`@nuxtjs/style-resources`, `nuxt-compress`, `nuxt-highlightjs`, `vue-svgicon`,
`v-click-outside`, `@nuxt/typescript-build`, `vue-template-compiler`, `vue-demi`, `vuex`,
`@vuex-orm/*`, `@vue/vue2-jest`, `vue-jest`, `frontmatter-markdown-loader`,
`@tiptap/vue-2`. Decision: `vue-vega` and `nuxt-mq` have **0 usages** → delete (verify first).

## 4. Architecture of the Change

The app's **domain/use-case layer is framework-agnostic** (`v1/domain`, `v1/infrastructure`
with ts-injecty DI). The migration deliberately keeps that layer's interfaces stable and only
swaps the **infrastructure adapters** that touch Nuxt/Vue. Three adapter swaps:

### 4a. HTTP adapter — plain axios in a plugin
- New `plugins/axios.ts` (Nuxt 4 plugin) creates one `axios` instance: `baseURL` `/api`,
  request interceptor adds the bearer token from AuthService, response interceptor ports the
  existing `AxiosErrorHandler` behavior, plus the cache plugin (`AxiosCache` / `axios-cache`).
- Instance is `provide`d via `useNuxtApp()` **and** registered into the existing ts-injecty
  container, so the ~20 repository classes keep their `constructor(private axios)` signature
  and `this.axios.get/post/...` call sites **unchanged**.
- `useAxiosExtension` `makePublic()` (used by `OAuthRepository` for unauthenticated calls) is
  reimplemented against the plain instance.

### 4b. Auth adapter — custom AuthService (Pinia-backed)
- New `~100-line` `AuthService implements IAuthService`: `setUserToken(token)`,
  `logout()`, `loggedIn` getter, `redirect()`. Token persisted (cookie via `useCookie`, the
  Nuxt-4 idiomatic store) and surfaced to the axios request interceptor.
- `middleware/route-guard.ts` and `middleware/me.ts` switch from `$auth.loggedIn` /
  `$auth.logout()` to the AuthService (resolved from DI / `useNuxtApp`).
- Login + OAuth use-cases (`auth-login-use-case`, `oauth-login-use-case`) are untouched —
  they already call the `IAuthService` interface. Federated OIDC stays in extralit-server.

### 4c. Icon adapter — custom `<svg-icon>`
- A Vue 3 SFC `<svg-icon name="…" />` + a small generation step that turns `static/icons/*.svg`
  into a registry the component renders by `name`. The existing `<svgicon name=… width=… …>`
  call signature is preserved (mechanical tag rename at most) so 79 sites don't get rewritten.
- The `svg-icon.element.ts` plugin is replaced by global component registration.

### 4d. Other adapters (small)
- `v-click-outside` directive plugin → internals call `onClickOutside` (`@vueuse/core`); 18
  consumer sites unchanged.
- `tooltip.directive.ts` (`new Vue`) → Vue 3 `createApp`/`render` mount.
- `base-toast/bus.js` (`new Vue` bus) → `mitt`.
- `format-number.ts` (`Vue.filter`) → exported helpers; `DatasetTotal.vue` calls the helper.
- `.md` loader → Vite `unplugin-vue-markdown` (or inline raw import) for frontmatter content.
- `@nuxtjs/style-resources` → `vite.css.preprocessorOptions.scss.additionalData`.
- `nuxt-compress` → Nitro `compressPublicAssets`. `nuxt-highlightjs` → `highlight.js` in a plugin.

## 5. Config Migration (`nuxt.config.ts`)
- `ssr: false`, `telemetry: false`, `generate.dir` → Nuxt 4 equivalents (`ssr: false` stays;
  static output via `nitro.static` / `nuxi generate`).
- `buildModules`/`modules` collapse into Nuxt 4 `modules`: `@pinia/nuxt`, `@nuxtjs/i18n`.
- `axios.proxy` (`/api/`, `/share-your-progress` → `API_BASE_URL`) → Nitro `routeRules` /
  `devProxy`. Preserve the dev proxy to `http://0.0.0.0:6900` default.
- `components` auto-import (`pathPrefix: false`, `level: 1`) → Nuxt 4 `components` config.
- `router.middleware` (`route-guard`, `me`) → Nuxt 4 global middleware (`middleware/*.global.ts`).
- `publicRuntimeConfig` → `runtimeConfig.public`.
- webpack `build.extend` rules (md loader, tabulator/mjs babel, terser keep_classnames) →
  Vite equivalents; most babel transforms become unnecessary under esbuild/Vite.

## 6. Sequencing (straight cutover on this branch)

Per the user's choice, this is a **single cutover branch** (not incremental Phase-0-on-Vue-2).
To keep it bisectable despite that, work proceeds in a **fixed dependency order** with the
**Playwright suite as the running acceptance gate** after the app first boots:

1. **Deps & config** — rewrite `package.json` (add/remove per §3), `nuxt.config.ts`,
   `tsconfig`, `vitest.config.ts`. App will not build yet.
2. **Infra adapters** — axios plugin + DI wiring, AuthService, `<svg-icon>`, directives,
   event bus, filters→helpers. Get `nuxi dev` to **boot**.
3. **Mechanical Vue-3 codemods** — `slot/slot-scope`→`v-slot` (35), `$listeners`→`$attrs` (4),
   `v-model` prop/event rename where custom inputs need it, composition-api import swaps (48).
4. **Heavy libs** — tabulator/interactjs client-guarding, tiptap-vue-3, vuedraggable@next, i18n v9.
5. **Boot → first Playwright run on chromium**; drive remaining failures to green page-by-page.
6. **Unit tests** — port Jest→Vitest (config + `propsData→props`, `contains→exists`,
   `createLocalVue→global.plugins`, `emitted('input')→emitted('update:modelValue')`).
7. **Lint + typecheck clean**, remove compat shims, lock versions.

## 7. Error Handling & Risk
- **Client-only globals** (`window`/`document` at import time in tabulator/interactjs) are the
  top regression risk in Nuxt 4 even under `ssr:false` (app-shell pass). Mitigation: dynamic
  `import()` in `onMounted`, or `.client.vue` / `<ClientOnly>`.
- **DI timing**: ts-injecty registrations that previously ran in a Nuxt-2 plugin must run in a
  Nuxt-4 plugin with correct ordering (axios + auth registered before repositories resolve).
- **i18n v9 config reshape** is the fiddliest config item; lazy + `no_prefix` + 4 locales must
  be preserved and spot-checked in the UI.
- **Rollback**: branch-isolated; `develop` is untouched until merge.

## 8. Testing Strategy
- **Vitest**: `environment: happy-dom`, `@nuxt/test-utils` for Nuxt auto-imports/`mockNuxtImport`.
  Port specs alongside the components they cover; the 79 specs are the unit regression net.
- **Playwright (authoritative)**: run `npx playwright test --project=chromium`. Backend is
  mocked, so green chromium == functional parity for covered flows. Firefox/webkit projects
  stay in config but chromium is the gate per the request.
- **Definition of done:** chromium e2e green + Vitest green + lint/typecheck clean + app boots
  via `npm run dev` and `npm run build` succeeds.

## 9. Open Items to Verify During Implementation
- Confirm `vuex`, `@vuex-orm/*`, `vue-vega`, `nuxt-mq` are truly unreferenced before deleting.
- Confirm the `.md` frontmatter content's actual consumers (which pages render it) to pick the
  Vite markdown approach.
- Confirm whether any test depends on `createLocalVue`-style DI so those get the `global.plugins` rewrite.
