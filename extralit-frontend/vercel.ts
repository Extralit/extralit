// Programmatic Vercel configuration (executed at build time on Vercel).
//
// The SPA is environment-agnostic: its axios client calls a *relative* `/api`
// (see plugins/2.axios.ts), so the backend is selected here by proxying `/api`
// (and `/share-your-progress`) at the Vercel edge — same-origin, so no CORS.
//
// `API_BASE_URL` is supplied per Vercel environment and baked into the rewrite
// destinations at build time:
//   - Production (main):      https://extralit-public-demo.hf.space   (HF extralit/public-demo)
//   - Preview (develop/PRs):  https://extralit-dev-develop.hf.space   (HF extralit-dev/develop)
//   - Per-PR override:        https://extralit-dev-pr-<n>.hf.space     (branch-scoped Preview var,
//                             set opportunistically by extralit-frontend.build-push-dev.yml)
import { routes, type VercelConfig } from "@vercel/config/v1";

const API_ORIGIN = (process.env.API_BASE_URL ?? "https://extralit-public-demo.hf.space").replace(/\/+$/, "");

const config: VercelConfig = {
  buildCommand: "npm run generate",
  outputDirectory: ".output/public",
  // Monorepo gate: only deploy when files under extralit-frontend/ changed. The Ignored Build
  // Step runs from the project Root Directory (extralit-frontend); `git diff --quiet` exits 0
  // (skip the build) when there's no diff in the path, and non-zero (proceed) when there is.
  // The ':/'-prefixed pathspec anchors to the repo root regardless of the working directory.
  // (Vercel's automatic monorepo skipping doesn't apply — this is a polyglot repo with no JS
  // workspaces, so non-frontend changes would otherwise be treated as global and rebuild.)
  ignoreCommand: "git diff --quiet HEAD^ HEAD -- :/extralit-frontend",
  // vercel.ts requires the routes.* helpers; plain { source, destination } objects fail schema
  // validation. `:path*` is path-to-regexp; the external absolute destination proxies the request.
  rewrites: [
    routes.rewrite("/api/:path*", `${API_ORIGIN}/api/:path*`),
    routes.rewrite("/share-your-progress/:path*", `${API_ORIGIN}/share-your-progress/:path*`),
    // SPA fallback: static files are served first; everything else gets the prerendered shell.
    routes.rewrite("/(.*)", "/index.html"),
  ],
};

export default config;
