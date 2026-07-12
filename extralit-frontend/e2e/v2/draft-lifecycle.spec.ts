import { createIsolatedRecord, expect, loadSeed, signIn, test } from "./fixtures";

// Seam C (spec §10.1-C): drafts have ZERO server-side tests. This spec is the gate:
// a draft restores into the form on reload while the projection still shows the suggestion;
// submitting then flips the projection to response. Uses its own isolated record so its
// submit at the end never contaminates another spec's clean-suggestion precondition.
test("draft persists in the form without touching the projection, then submits", async ({ page, request }) => {
  const seed = loadSeed();
  const { reference, recordId } = await createIsolatedRecord(request, `${seed.reference}-draft-lifecycle`);

  await signIn(page);
  await page.goto(`/references/${encodeURIComponent(reference)}?workspace_id=${seed.workspaceId}`);

  const sizeCell = page.locator("[data-question='size']");
  const editor = sizeCell.locator("[contenteditable]");
  await editor.click();
  await editor.fill("777");

  const draftPut = page.waitForResponse(
    (r) => r.url().includes(`/records/${recordId}/responses`) && r.request().method() === "PUT"
  );
  await page.locator(`[data-test='save-draft-${recordId}']`).click();
  expect((await draftPut).status()).toBe(200);

  await page.reload();
  // Form restores the draft value...
  await expect(sizeCell.locator("[contenteditable]")).toHaveText("777");
  // ...but the projection still resolves the suggestion (draft must not project).
  await expect(sizeCell.getByText("Suggestion")).toBeVisible();

  await page.locator(`[data-test='submit-${recordId}']`).click();
  await page.reload();
  await expect(sizeCell.getByText("Response")).toBeVisible();
});
