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
> The Playwright e2e suite is inherited from upstream Argilla and is currently **out of
> sync with Extralit's sign-in UI** (its login helper targets placeholders/buttons Extralit
> no longer renders), so it is not a passing gate as-is and needs a dedicated reconciliation
> pass. The local Playwright browser also can't launch on the Orin dev host (missing OS libs,
> no sudo) — run e2e in CI.

## Code Quality

```bash
npm run lint             # ESLint check (eslint 8 + vue-eslint-parser)
npm run lint:fix         # Fix ESLint issues
npm run format           # Format with Prettier
npm run format:check     # Check formatting
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
- ESLint 8 + Prettier

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
