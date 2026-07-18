import { test as base, chromium, type APIRequestContext, type Browser } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export interface SeedOutput {
  workspaceId: string;
  schemaId: string;
  schemaName: string;
  reference: string;
  recordId: string;
  questions: Record<string, { id: string; name: string }>;
}

export const loadSeed = (): SeedOutput =>
  JSON.parse(readFileSync(join(__dirname, "seed", "seed-output.json"), "utf-8"));

export const credentials = () => ({
  username: process.env.E2E_USERNAME ?? "extralit",
  password: process.env.E2E_PASSWORD ?? "12345678",
});

const apiUrl = () => process.env.E2E_API_URL ?? "http://localhost:6900";

export const apiToken = async (request: APIRequestContext): Promise<string> => {
  const { username, password } = credentials();
  const res = await request.post(`${apiUrl()}/api/v2/token`, { form: { username, password } });
  return (await res.json()).access_token;
};

// Create a fresh record under the seeded schema with its OWN reference plus a seeded
// suggestion on the `size` question. Response-mutating specs (review-loop, draft-lifecycle)
// each seed one of these in beforeEach so they never share the single seed record — which
// otherwise races in parallel and, in serial order, leaves a submitted response that breaks
// the next spec's clean "Suggestion" precondition (roborev job 154). A reseed wipes the schema.
// The reference must NOT contain seed.reference as a substring: other specs assert on the
// shared record via non-exact getByText(seed.reference), and a superstring reference in the
// same schema substring-matches those assertions into strict-mode violations (roborev job 157).
export const createIsolatedRecord = async (
  request: APIRequestContext,
  reference: string
): Promise<{ reference: string; recordId: string }> => {
  const seed = loadSeed();
  const headers = { Authorization: `Bearer ${await apiToken(request)}` };

  const upsert = await request.post(`${apiUrl()}/api/v2/schemas/${seed.schemaId}/records:bulk-upsert`, {
    headers,
    data: { items: [{ fields: { size: "120", label: "control", country: "KE" }, reference }] },
  });
  const recordId = (await upsert.json()).items[0].id;

  await request.put(`${apiUrl()}/api/v2/records/${recordId}/suggestions`, {
    headers,
    data: { question_id: seed.questions.size.id, value: "120", score: 0.87, agent: "e2e-seeder" },
  });
  await request.post(`${apiUrl()}/api/v2/schemas/${seed.schemaId}:rebuild-index`, { headers });

  return { reference, recordId };
};

// Local chromium cannot launch on the Orin dev host — connect to the remote ccui
// chromium over CDP when E2E_CDP_URL is set; fall back to a plain launch (CI).
export const test = base.extend<object, { browser: Browser }>({
  browser: [
    async ({}, use) => {
      const cdpUrl = process.env.E2E_CDP_URL;
      const browser = cdpUrl ? await chromium.connectOverCDP(cdpUrl) : await chromium.launch();
      await use(browser);
      await browser.close();
    },
    { scope: "worker" },
  ],
});

export const expect = test.expect;

// Real-backend sign-in through the actual UI: this is seam A — the first bearer-token
// client of /api/v2. No route mocking anywhere in e2e/v2.
export const signIn = async (page: import("@playwright/test").Page) => {
  const { username, password } = credentials();
  await page.goto("/sign-in");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"));
};
