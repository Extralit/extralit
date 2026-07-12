import { defineConfig, devices } from "@playwright/test";

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: "./e2e",
  snapshotPathTemplate: "{testDir}/{testFileDir}/__screenshots__/{projectName}/{arg}{ext}",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 3,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",

  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.1 },
  },

  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",

    trace: "on-first-retry",
  },

  projects: [
    // Legacy Argilla specs — kept out of the v2 suite (they are not a v2 gate).
    {
      name: "chromium",
      testIgnore: "v2/**",
      use: { ...devices["Desktop Chrome"] },
    },

    {
      name: "firefox",
      testIgnore: "v2/**",
      use: { ...devices["Desktop Firefox"] },
    },

    {
      name: "webkit",
      testIgnore: "v2/**",
      use: { ...devices["Desktop Safari"] },
    },

    // v2 vertical slice, real backend, no network mocks. Run with `playwright test --project=v2`.
    {
      name: "v2",
      testMatch: "v2/**/*.spec.ts",
      retries: 0, // real backend: retries mask seeding/state bugs
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.E2E_BASE_URL ?? process.env.BASE_URL ?? "http://localhost:3000",
      },
    },
  ],

  webServer: {
    command: process.env.API_BASE_URL ? `API_BASE_URL=${process.env.API_BASE_URL} npm run dev` : "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
  },
});
