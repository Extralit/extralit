import { createIsolatedRecord, expect, loadSeed, signIn, test } from "./fixtures";

// The core product loop (spec §10.2-3): suggestion shown with provenance → edit → submit →
// projection re-read flips source to response. Never chained over HTTP in the server suites.
// Uses its own isolated record so it never shares mutable response state with other specs.
test("converts a suggestion into a submitted response", async ({ page, request }) => {
  const seed = loadSeed();
  const { reference, recordId } = await createIsolatedRecord(request, "10.2000/e2e-review-loop");

  await signIn(page);
  await page.goto(`/references/${encodeURIComponent(reference)}?workspace_id=${seed.workspaceId}`);

  const sizeCell = page.locator("[data-question='size']");
  await expect(sizeCell).toBeVisible();
  await expect(sizeCell.getByText("Suggestion")).toBeVisible();
  await expect(sizeCell.getByText("e2e-seeder")).toBeVisible();

  // Edit the text answer (ContentEditableFeedbackTask renders a contenteditable paragraph).
  const editor = sizeCell.locator("[contenteditable]");
  await editor.click();
  await editor.fill("135");

  const putResponse = page.waitForResponse(
    (r) => r.url().includes(`/api/v2/records/${recordId}/responses`) && r.request().method() === "PUT"
  );
  await page.locator(`[data-test='submit-${recordId}']`).click();
  expect((await putResponse).status()).toBe(200);

  // Reload: the projection must now resolve from the submitted response.
  await page.reload();
  await expect(sizeCell.getByText("Response")).toBeVisible();
  await expect(sizeCell.getByText("Suggestion")).not.toBeVisible();
});
