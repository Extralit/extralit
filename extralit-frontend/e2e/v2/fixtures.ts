import { test as base, chromium, type Browser } from "@playwright/test";
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
