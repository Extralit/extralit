# extralit-frontend Setup

## Installation

```bash
cd extralit-frontend/

# Install dependencies
npm install
```

## Development

```bash
npm run dev              # Development server
npm run build            # Production build
```

## Running with existing server API

```bash
API_BASE_URL=https://extralit-public-demo.hf.space/ npm run dev
```

## Testing

```bash
npm run test             # Vitest unit tests (run once)
npm run test:watch       # Watch mode
npm run test:coverage    # With coverage

npm run e2e              # Playwright e2e (interactive)
npm run e2e:silent       # Playwright headless
npm run e2e:report       # View test report
```

> Unit tests run on **Vitest** (`vitest.config.ts` + `test/setup.ts`), using
> `@vue/test-utils` v2 and `@nuxt/test-utils`. Specs needing Nuxt runtime context use
> `// @vitest-environment nuxt` or `mockNuxtImport`.
>
> The Playwright e2e suite is inherited from upstream Argilla. The shared login helper
> (`e2e/common/login-and-wait-for.ts`) has been reconciled to Extralit's real sign-in UI:
> it fills `getByLabel("Username"/"Password")`, submits the `"Sign in"` button, mocks
> `/api/v1/token` + `/api/v1/me` offline, and waits for the home/datasets landing at `/`
> (there is no `/datasets` route). This flow is runtime-verified via the CDP browser. The
> per-page specs still need fresh Extralit screenshot baselines (`--update-snapshots`); the
> inherited ones are Argilla's. The local Playwright chromium **does** launch on the Orin
> host (verified 2026-07-18: `chromium.launch({headless:true})` → Chrome 149 after a plain
> `npx playwright install chromium`; no `install-deps`/sudo needed), so the headless gate
> can run locally as well as in CI.

## extraction e2e suite (`e2e/extraction/`, real backend — the extraction slice's integration gate)

Separate Playwright project (`--project=extraction`, `testMatch: extraction/**/*.spec.ts`);
the legacy Argilla specs above are **not** an extraction gate. No network mocking — it
exercises real bearer auth on `/api/v1`, slashed-DOI encoding, the suggestion→response loop,
drafts and search freshness. Env knobs (see `e2e/extraction/fixtures.ts`): `E2E_API_URL`
(default `http://localhost:6900`), `E2E_BASE_URL`/`BASE_URL` (default `http://localhost:3000`),
`E2E_USERNAME`/`E2E_PASSWORD` (default `extralit`/`12345678`), optional `E2E_CDP_URL` to drive
a remote chromium.

```bash
npm run e2e:extraction:seed   # uv run ../extralit-server python e2e/extraction/seed/seed_v2_e2e.py
npm run dev -- --host         # dev server reachable from the browser
npm run e2e:extraction        # playwright test --project=extraction (local chromium)
```

Requires the full stack up with the server on :6900. On the Orin host the backing services
publish to `localhost` (postgres :5432, minio :9000, elasticsearch :9200) but the compose
`redis` is **not** published, and the server `.env` uses docker-network hostnames
(`minio`/`elasticsearch`/`redis`) — running the server on the host needs those overridden
to `localhost` plus a throwaway redis on :6379.

## Code Quality

```bash
npm run lint             # oxlint, then eslint 10 (vue-eslint-parser) — both --quiet
npm run lint:oxc         # oxlint only (the blocking CI gate; ~1s)
npm run lint:eslint      # eslint only (Vue template + i18n rules; advisory in CI)
npm run lint:fix         # Autofix both linters
npm run format           # Format with oxfmt
npm run format:check     # Check formatting (blocking in CI)
npm run generate-icons   # Generate icon components from SVG

npx nuxi typecheck       # vue-tsc type check
npm run build            # Production build (vite/nitro)
```

## Requirements

- Node.js 18+ (developed on Node 24)
- Backend server running for full functionality

## Architecture

- **v1/** directory: Pinia + domain-driven design (entities, use cases, dependency injection
  via `ts-injecty`). The domain/use-case layer is framework-agnostic; only the Vue/Nuxt
  adapters (HTTP, Auth, Icons) were swapped during the Vue 3 / Nuxt 4 migration.
- Component hierarchy: base (stateless) → features (page-specific) → global (reusable)
- HTTP: plain `axios` in `plugins/2.axios.ts` (replaced `@nuxtjs/axios`), re-injected into DI.
- Auth: `AuthService` (`v1/infrastructure/services/AuthService.ts`) implementing `IAuthService`,
  provided as `$auth` by `plugins/1.auth.ts` (replaced `@nuxtjs/auth-next`).
- Icons: custom `<svg-icon>` (`components/base/BaseSvgIcon.vue`) reading `static/icons/*.svg`
  (replaced `vue-svgicon`).
- Plugins load in order via numeric prefixes (`1.auth` → `2.axios` → `3.di`); middleware are
  Nuxt-4 globals (`middleware/*.global.ts`).

> **TS posture:** `tsconfig.json` keeps `strict:false` (matching the pre-Vue3 config) and
> disables Nuxt-4's new `verbatimModuleSyntax`/`noImplicitOverride`. Tightening to strict is a
> separate hardening effort. Note: Vite/esbuild (`isolatedModules`) requires type-only imports
> to use the inline `import { type X }` modifier or they throw at runtime in dev.

## Key Technologies

- Vue 3.5 + Nuxt 4 (Vite + Nitro)
- Pinia (state management; Vuex fully removed)
- Vitest + @vue/test-utils v2 (unit) + Playwright (e2e)
- @nuxtjs/i18n v10 (vue-i18n v11), @vueuse/core, mitt
- oxlint + ESLint 10 (lint), oxfmt (format)

## Structure

```
/components      # Vue components
/v1              # New Pinia architecture
/pages           # Nuxt pages
/layouts         # Layouts
/plugins         # Plugins
/middleware      # Middleware
/assets          # Static assets
/e2e             # Playwright tests
```
