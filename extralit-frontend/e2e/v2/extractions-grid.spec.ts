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

  // Scoped to the grid's own testid (the `<perspective-viewer>` element itself carries
  // `data-testid="extractions-grid"`) rather than unscoped `page.getByText(...)`: Playwright
  // pierces open shadow roots for CSS/text engines when the locator is rooted inside the
  // shadow host, so scoping here still reaches cells rendered in the datagrid's shadow DOM.
  const grid = page.getByTestId("extractions-grid");
  await expect(grid).toBeVisible();

  // Column manifest: both schemas appear — including the record-less one (coverage map).
  await expect(grid.getByText(`${seed.schemaName}.size`, { exact: true })).toBeVisible();
  await expect(grid.getByText(`${seed.emptySchemaName}.notes`, { exact: true })).toBeVisible();

  // Rows + coalesced values: suggestion-sourced `size`, response-beats-suggestion `label`.
  await expect(grid.getByText(seed.reference, { exact: true }).first()).toBeVisible();
  await expect(grid.getByText("120", { exact: true }).first()).toBeVisible();
  await expect(grid.getByText("control", { exact: true }).first()).toBeVisible();
  await expect(grid.getByText("intervention", { exact: true })).toHaveCount(0);
  // The record's raw `size`/`label` fields ("999"/"unset") are deliberately distinct from the
  // suggestion/response values above (see seed_v2_e2e.py) — if the projection ever regressed
  // to resolving cells from raw fields instead of coalescing suggestion/response, this raw
  // value would appear in the grid and this assertion would fail.
  await expect(grid.getByText("999", { exact: true })).toHaveCount(0);
});
