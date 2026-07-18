# v2 e2e suite (real backend, remote chromium)

Prereqs: full local stack up (`docker-compose up -d`, server on :6900), then:

1. Seed:      `npm run e2e:v2:seed`
2. Dev server reachable from the browser container: `npm run dev -- --host`
3. Run:
   ```
   E2E_CDP_URL=http://ccui:9222 \
   E2E_BASE_URL=http://<this-host-lan-ip>:3000 \
   npm run e2e:v2
   ```

Without `E2E_CDP_URL` (e.g. CI) a local chromium is launched. No network mocking:
these specs gate real auth (bearer on /api/v2), slashed-DOI encoding, the
suggestion→response loop, drafts and search freshness. The legacy Argilla specs
under e2e/* are not a gate for v2 work.
