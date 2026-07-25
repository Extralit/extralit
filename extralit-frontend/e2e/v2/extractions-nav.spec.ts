import { expect, signIn, test } from "./fixtures";

/**
 * The `/extractions` page is reachable from the home tab bar.
 *
 * `schemas` and `extractions` are *navigation* tabs (see `NAVIGATION_TAB_ROUTES` in
 * `pages/index.vue`): unlike `datasets`/`documents`, which swap the panel below the tab bar,
 * selecting one routes to a page of its own. Asserted against the real backend rather than a
 * mocked mount because the failure this guards against — a tab that renders but routes
 * nowhere — is a router-level behaviour a shallowMount would stub away.
 *
 * Needs no seed: the tab bar and the route are workspace-independent.
 */
test("home exposes an Extractions tab, after Datasets/Documents/Schemas, that opens /extractions", async ({ page }) => {
  await signIn(page);
  await page.goto("/");

  const tabs = page.locator(".tabs .tab__button");
  await expect(tabs).toHaveCount(4);
  // Order matters: the tab was specified to sit after the three existing ones.
  await expect(tabs).toHaveText([/Datasets/i, /Documents/i, /Schemas/i, /Extractions/i]);

  await tabs.filter({ hasText: /Extractions/i }).click();
  await page.waitForURL((url) => url.pathname === "/extractions");

  // Landed on the real page, not a blank route: its title renders regardless of whether the
  // selected workspace has any extractions.
  await expect(page.getByRole("heading", { name: "Extractions" })).toBeVisible();
});
