import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam A (spec §10.1-A): gates that a real UI sign-in produces a bearer token which the
// schemas-list request carries end-to-end against a live /api/v1. Nothing here is mocked.
test("signs in with a bearer token, lists schemas, opens records", async ({ page }) => {
  const seed = loadSeed();

  // The /schemas list renders for the *selected* workspace, and the app auto-selects the
  // first one — non-deterministic across backends. Pin the persisted selection to the
  // seeded workspace so saveWorkspaces() restores it regardless of workspace ordering.
  await page.addInitScript((workspaceId) => {
    localStorage.setItem("extralit-selected-workspace-id", workspaceId);
  }, seed.workspaceId);

  await signIn(page);

  // Armed only AFTER signIn: /api/v1/me/datasets has a second in-app caller,
  // DatasetRepository.fetchFeedbackDatasets(), which fires param-less on the post-login
  // landing page. Arming earlier latches onto that one instead and the assertions below
  // would describe the home page's request rather than the schemas page's. The
  // `workspace_id` param is what distinguishes SchemaRepository.getSchemas() from it.
  const schemasRequest = page.waitForResponse(
    (r) => /\/api\/v1\/me\/datasets\?[^/]*workspace_id=/.test(r.url()) && r.request().method() === "GET"
  );
  await page.goto("/schemas");

  const schemasResponse = await schemasRequest;
  expect(schemasResponse.status()).toBe(200);
  expect(schemasResponse.request().headers()["authorization"]).toMatch(/^Bearer /);

  await expect(page.getByText(seed.schemaName)).toBeVisible();

  await page.getByText(seed.schemaName).click();
  await expect(page.getByText(seed.reference)).toBeVisible();
});
