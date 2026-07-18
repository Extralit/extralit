import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam B (spec §10.1-B): %2F-encoded DOI through Nuxt devProxy + uvicorn, untested server-side
// for the projection route. Assert both v2 reference endpoints round-trip.
test("opens a reference containing a slash via the encoded URL", async ({ page }) => {
  const seed = loadSeed();
  await signIn(page);

  const projectionRequest = page.waitForResponse(
    (r) => r.url().includes("/api/v2/projection/references/") && r.request().method() === "GET"
  );
  const recordsRequest = page.waitForResponse(
    (r) => r.url().includes(`/api/v2/schemas/${seed.schemaId}/records`) && r.request().method() === "GET"
  );

  await page.goto(`/references/${encodeURIComponent(seed.reference)}?workspace_id=${seed.workspaceId}`);

  expect((await projectionRequest).status()).toBe(200);
  expect((await recordsRequest).status()).toBe(200);

  await expect(page.getByText(seed.reference)).toBeVisible();
  await expect(page.locator("[data-question='size']")).toBeVisible();
});
