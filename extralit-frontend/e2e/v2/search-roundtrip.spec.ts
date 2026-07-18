import { expect, loadSeed, signIn, test } from "./fixtures";

// Seam D (spec §10.1-D): first real write→search freshness check anywhere. The index is
// best-effort/eventually consistent — poll with expect.toPass instead of asserting once.
test("FTS finds the seeded record; filters and empty results render gracefully", async ({ page }) => {
  const seed = loadSeed();
  await signIn(page);
  await page.goto(`/schemas/${seed.schemaId}`);
  await expect(page.getByText(seed.reference)).toBeVisible();

  const searchBox = page.getByPlaceholder("Search records…");

  await expect(async () => {
    await searchBox.fill("control");
    await searchBox.press("Enter");
    await expect(page.getByText(seed.reference)).toBeVisible({ timeout: 2_000 });
  }).toPass({ timeout: 30_000 }); // eventual consistency window

  // Filtered search: status filter travels through the :search body.
  await page.locator("select").selectOption("pending");
  await expect(page.getByText(seed.reference)).toBeVisible();

  // Graceful empty state — copy must not claim "0 records exist" (total is approximate).
  await searchBox.fill("zzz-no-such-token-zzz");
  await searchBox.press("Enter");
  await expect(page.getByText("No records match this search.")).toBeVisible();
});
