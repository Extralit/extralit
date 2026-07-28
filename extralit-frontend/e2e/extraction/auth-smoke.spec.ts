import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam A (spec §10.1-A): first bearer-token client of /api/v2 — no server test sends
// Authorization: Bearer or a CORS Origin to a v2 route. Nothing here is mocked.
test("signs in with a bearer token, lists schemas, opens records", async ({ page }) => {
  const seed = loadSeed();

  // The /schemas list renders for the *selected* workspace, and the app auto-selects the
  // first one — non-deterministic across backends. Pin the persisted selection to the
  // seeded workspace so saveWorkspaces() restores it regardless of workspace ordering.
  await page.addInitScript((workspaceId) => {
    localStorage.setItem("extralit-selected-workspace-id", workspaceId);
  }, seed.workspaceId);

  const schemasRequest = page.waitForResponse(
    (r) => r.url().includes("/api/v2/schemas") && r.request().method() === "GET"
  );
  await signIn(page);
  await page.goto("/schemas");

  const schemasResponse = await schemasRequest;
  expect(schemasResponse.status()).toBe(200);
  expect(schemasResponse.request().headers()["authorization"]).toMatch(/^Bearer /);

  await expect(page.getByText(seed.schemaName)).toBeVisible();

  await page.getByText(seed.schemaName).click();
  await expect(page.getByText(seed.reference)).toBeVisible();
});
