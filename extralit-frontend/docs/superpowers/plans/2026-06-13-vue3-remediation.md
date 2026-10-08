# Vue 3 / Nuxt 4 Remediation Plan (session 4)

**Date:** 2026-06-13 · **Branch:** `feat/vue-v2-to-v3` · **Checkout:** main repo `/home/jonny/Projects/Extralit/extralit/extralit-frontend` (worktree was removed; node_modules is being reinstalled to Nuxt 4 via `npm ci`).

Combines (a) the 5 substantive open roborev reviews and (b) verified gaps from the Nuxt-4 / Vue-3 migration docs not covered by the original design doc. Each task is independently verifiable; gate after each with `npx nuxi typecheck` + `npx vitest run` + `npm run lint` (and `nuxi build` for config changes).

Source review IDs (roborev): 2,3,4,5,6 substantive; 8,9,11 = prior-agent "CLI blocked" noise → close with comment, no code change. (10 is on `develop`, not ours.)

---

## TIER 1 — Real bugs (must fix)

### T1.1 — Dynamic routes: `_param` → `[param]` (Nuxt 4 file-router) — PENDING FINAL VERIFY

Nuxt 4 requires bracket dynamic segments; `_id.vue` becomes a _literal_ `/dataset/_id` route, so `/dataset/<uuid>` 404s. Static `/sign-in` works (why the app "boots"), but no dynamic flow was ever runtime-tested (handoff gap #5; e2e never green). **Verify via `nuxi prepare` route manifest once Nuxt 4 is installed before executing.**
Renames (use `git mv`):

- `pages/new/_id.vue` → `pages/new/[id].vue`
- `pages/new/hf/_repoId.vue` → `pages/new/hf/[repoId].vue`
- `pages/new/import/_id.vue` → `pages/new/import/[id].vue`
- `pages/oauth/_provider/` → `pages/oauth/[provider]/`
- `pages/dataset/_id/` (subtree) → `pages/dataset/[id]/`
  Then: audit `middleware/01.route-guard.global.ts` (+`02.me`) route-name switches, all `<NuxtLink :to>` / `router.push`/`useRoute().params`, and `useRoute().params.id` access. Confirm generated route names. Gate: typecheck + boot + navigate a dataset route in dev.

### T1.2 — Span entity factory leak (review 3, MEDIUM)

`v1/.../useSpanAnnotationTextFieldViewModel.ts:48-71` `entityComponentFactory` does `createApp().mount()` but never `unmount()`. `Highlighting.applyEntityStyle()` (`highlighting.ts:323-344`) tears down + recreates on every scroll/resize/hover/span-change → unbounded live apps + orphaned scroll listeners (`EntityComponent.beforeUnmount` never fires). Fix: factory returns `{ element, unmount }`; caller unmounts before `removeChild` and in `Highlighting.unmount()`.

### T1.3 — `head()` options hook (B5)

`pages/dataset/[id]/annotation-mode/index.vue:44` uses Nuxt-2 `head(){...}` (no-op in Nuxt 4; title never set). Replace with `useHead(() => ({ title: ... }))` in `setup()`.

### T1.4 — base-date snapshot pollution (review 5, MEDIUM)

`components/base/base-date/base-date.test.ts` `toMatchSnapshot()` on the VueWrapper → 2400+ lines incl. leaked absolute path `/home/jonny/...` and `"version":"3.5.38"`. Fix: `expect(baseDate.html()).toMatchSnapshot()` (all 10 assertions), drop `vi.useFakeTimers("modern")` arg, regenerate snapshots, delete stale Jest-keyed entries in `base-date.test.ts.snap` + `BaseSlider.spec.js.snap`.

---

## TIER 2 — Real correctness / bounded (should fix)

### T2.1 — Transition CSS class rename (C2, 9 files)

Vue 3 renamed `.x-enter`→`.x-enter-from`, `.x-leave-to` unchanged. 9 files use old `.x-enter` (silently ignored → broken enter animation): BaseFlowModal, BaseModal, Toast, BaseCardWithTabs, DatasetUpdateDialog, EntityLabelSelection.component, LabelSelection.component, DatasetFilters (`.filterAppear-enter`), ImportFromHub (`.slide-right-enter`). Rename selectors.

### T2.2 — `$slots.default` array API (C3, 2 files)

Vue 3: `$slots.default` is a function; VNodes lack `.elm`/`.tag`/`.context`.

- `components/base/base-scroll/SynchronizeScroll.vue:15` reads `.tag`/`.elm` → rewrite via template ref / `onMounted` DOM collection.
- `RatingShortcuts.vue:17` reads `$slots.default[0].context?.question...` → refactor to receive `question` as a prop.

### T2.3 — `v-html` into `<style>` (review 6, 3 files)

`<component :is="'style'" v-html=...>` is a `</style>`-breakout sink. TextField.vue:435, ChatField.vue:303, SpanAnnotationTextField.vue:365 → bind as text child `{{ highlightStyles }}` instead. Also drop stray `:key="id"` (TextField vs ChatField inconsistency).

### T2.4 — `$attrs` class/style (C5, 4 files) — VERIFY each

Vue 3 `$attrs` now includes class/style. Audit BaseBadge, EntityBadge, FilterTooltip, FilterBadge: if they `v-bind="$attrs"` on a non-root element, add `inheritAttrs:false` to avoid double class/style. Fix only the ones that actually double-bind.

### T2.5 — Config cleanups

- `.eslintrc.js`: `localeDir: "./translation/*.json"` → `*.js` (i18n lint is currently a no-op) (A5).
- `nuxt.config.ts`: remove `pdfjs-dist` from `build.transpile` (dead — not a dep) (A7).
- `package.json`: remove `core-js` dep (no source import; only vendored handlebars references it) (A1).
- `package.json` overrides: verify `@intlify/*` pins match transitive names in `package-lock.json`; drop any inert pin (e.g. nonexistent `@intlify/core`) (review 2).

### T2.6 — Nuxt error page (B2)

`layouts/error.vue` is only a named layout, not Nuxt's error page. Create root `error.vue` (move/adapt), replace options `layout:"error"` with `definePageMeta`/`<NuxtLayout>`, update legacy `<svgicon>`→`<svg-icon>` if present.

---

## TIER 3 — Best-practice, scoped (judgment)

### T3.1 — `emits` declarations (C1) — SCOPED, not blanket

105 files `$emit` without `emits`. Blanket-editing all 105 is over-reach. **Scope to the dangerous subset:** components emitting _native-DOM-event names_ (`click`,`input`,`change`,`focus`,`blur`,`submit`,`keydown`,`mouseover`,`mouseleave`,`mousedown`,`scroll`) — without `emits` these fall through to the root element and double-fire. Audit + fix that subset (esp. base/* inputs/buttons). Pure custom-event components: defer to a follow-up note unless trivially batched.

### T3.2 — `runtimeConfig.public.apiBaseUrl` (A6) — optional

`API_BASE_URL` is read at build time only → HF/Docker can't repoint backend without rebuild. Add `runtimeConfig.public.apiBaseUrl` consumed in `plugins/2.axios.ts`; keep `/api` dev proxy. Enables `NUXT_PUBLIC_API_BASE_URL` override. Only if it doesn't destabilize the axios DI wiring.

### T3.3 — Review 4 (type-only imports) — RESPOND, likely no code change

`nuxi typecheck` already passes at 0 with the deliberate `strict:false`/`verbatimModuleSyntax:false` posture. The reviewer's "value-used-as-type" risk is covered by the passing typecheck + verified boot. Do a quick targeted check (grep flagged `type`-only specifiers for runtime value use); if clean, close with rationale rather than re-enabling strict (separate hardening effort per handoff #4).

---

## Out of scope (note as follow-ups, do not do here)

- Playwright e2e reconciliation (handoff #2) — dedicated effort, can't run on this host.
- PDF viewer real implementation (handoff #3) — user-owned dep rebuild.
- Full `strict:true` TS hardening (handoff #4).
- `@nuxt/eslint` module swap (A4) / eslintrc ESM (A3) — lint passes; enhancement only.

## Verification gate (run after each tier, from `extralit-frontend/`, `NUXT_IGNORE_LOCK=1` prefix)

1. `npx vitest run` — ≥735 pass
2. `npx nuxi typecheck` — 0 errors
3. `npm run lint` — 0 errors
4. `npx nuxi build` — clean (after any config/route change)
5. Boot `npm run dev`, drive a dynamic route (datasets/annotation) via the CDP browser for T1.1/T1.2.

## Closing roborev

After fixes + green gates: `roborev comment`/`roborev close` reviews 2,3,5,6 (fixed), 4 (responded), 8/9/11 (noise). Needs CLI approval.
