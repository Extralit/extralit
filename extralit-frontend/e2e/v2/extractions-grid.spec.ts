import { expect, loadSeed, signIn, test } from "./fixtures";

// Replacement gate for the deleted review-loop specs (spec §3.5 accepted risk):
// seed → grid renders coalesced values → coverage-gap columns present.
test("extraction table renders coalesced values and coverage gaps", async ({ page }) => {
  const seed = loadSeed();
  await signIn(page);

  const projectionRequest = page.waitForResponse(
    (r) =>
      r.url().includes("/api/v2/projection") &&
      !r.url().includes("/references/") &&
      r.request().method() === "GET"
  );
  await page.goto(`/extractions?workspace_id=${seed.workspaceId}`);
  expect((await projectionRequest).status()).toBe(200);

  const viewer = page.locator("perspective-viewer");
  await expect(viewer).toBeVisible();

  // Column manifest: both schemas appear — including the record-less one (coverage map).
  await expect(page.getByText(`${seed.schemaName}.size`)).toBeVisible();
  await expect(page.getByText(`${seed.emptySchemaName}.notes`)).toBeVisible();

  // Rows + coalesced values: suggestion-sourced `size`, response-beats-suggestion `label`.
  await expect(page.getByText(seed.reference).first()).toBeVisible();
  await expect(page.getByText("120").first()).toBeVisible();
  await expect(page.getByText("control").first()).toBeVisible();
  await expect(page.getByText("intervention")).toHaveCount(0);
});
