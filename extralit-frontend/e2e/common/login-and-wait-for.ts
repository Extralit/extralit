import { Page } from "@playwright/test";

export type Role = "admin" | "owner" | "annotator";

const FAKE_TOKEN = "FAKE_ACCESS_TOKEN";

/**
 * Logs in through the real Extralit sign-in UI with the network mocked, so the
 * flow is deterministic and needs no backend.
 *
 * Selectors match the current DOM (see pages/sign-in.vue +
 * components/features/login/components/LoginInput.vue): the username/password
 * inputs expose their label as the accessible name ("Username"/"Password") and
 * the submit control is a <base-button type="submit"> rendering the i18n label
 * button.login ("Sign in").
 *
 * @param waitForURL Path the app should land on after login. The datasets list
 *   is served at "/" (there is no "/datasets" route), so "datasets", "/" and ""
 *   are all treated as "home"; any other value is awaited as `**\/${value}`.
 */
export const loginUserAndWaitFor = async (page: Page, waitForURL: string = "/", role: Role = "admin") => {
  // POST /api/v1/token -> issue a fake bearer token (no backend).
  await page.route("*/**/api/v1/token", async (route) => {
    await route.fulfill({
      json: { access_token: FAKE_TOKEN, token_type: "bearer" },
    });
  });

  // GET /api/v1/me -> the authenticated user the app loads after login.
  await page.route("*/**/api/v1/me", async (route) => {
    await route.fulfill({
      json: {
        id: "00000000-0000-0000-0000-000000000001",
        username: "FAKE_USER",
        first_name: "FAKE",
        last_name: "USER",
        full_name: "FAKE_USER",
        role,
        api_key: "FAKE_API_KEY",
        workspaces: ["WORKSPACE 1"],
        inserted_at: "2024-01-01T00:00:00.000000",
        updated_at: "2024-01-01T00:00:00.000000",
      },
    });
  });

  await page.goto("/sign-in");

  await page.getByLabel("Username").fill("damian");
  await page.getByLabel("Password").fill("12345678");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();

  const landsOnHome = waitForURL === "datasets" || waitForURL === "/" || waitForURL === "";

  if (landsOnHome) {
    // Login succeeds once we leave the sign-in page for the home/datasets list.
    await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"));
  } else {
    await page.waitForURL(`**/${waitForURL}`);
  }
};
