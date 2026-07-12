import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam A (spec §10.1-A): first bearer-token client of /api/v2 — no server test sends
// Authorization: Bearer or a CORS Origin to a v2 route. Nothing here is mocked.
test("signs in with a bearer token, lists schemas, opens records", async ({ page }) => {
  const seed = loadSeed();

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
