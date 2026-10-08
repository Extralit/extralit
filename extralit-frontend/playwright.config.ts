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
    // Legacy Argilla specs — kept out of the extraction suite (they are not a gate for it).
    {
      name: "chromium",
      testIgnore: "extraction/**",
      use: { ...devices["Desktop Chrome"] },
    },

    {
      name: "firefox",
      testIgnore: "extraction/**",
      use: { ...devices["Desktop Firefox"] },
    },

    {
      name: "webkit",
      testIgnore: "extraction/**",
      use: { ...devices["Desktop Safari"] },
    },

    // Extraction vertical slice, real backend, no network mocks. Run with `playwright test --project=extraction`.
    {
      name: "extraction",
      testMatch: "extraction/**/*.spec.ts",
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
