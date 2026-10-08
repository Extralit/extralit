/**
 * Records a demo of the PR #234 /extractions Perspective grid against a LIVE stack
 * (extralit-server :6900 + nuxt dev :3000), and asserts each demoed behaviour as it goes.
 *
 * It is a demo AND a gate: every scene calls `check()`, and a failing check aborts with a
 * non-zero exit so a broken UI can never be dressed up as a passing video.
 *
 * Outputs (into --out):
 *   video/*.webm     raw headless-chromium screen recording
 *   timeline.json    scene boundaries (ms from recording start) + pass/fail, for Remotion
 *   shots/*.png      one still per scene
 *   console.log      browser console + pageerror capture
 *
 * Run from extralit-frontend/ (so `playwright` resolves):
 *   node <this> --out /path/to/out
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { join } from "node:path";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 ? fallback : process.argv[i + 1];
};

const OUT = arg("out", "/tmp/extractions-demo");
const BASE = arg("base", "http://localhost:3000");
const SEED = JSON.parse(readFileSync(arg("seed"), "utf-8"));
const E2E_SEED = JSON.parse(readFileSync(arg("e2e-seed"), "utf-8"));
const WIDTH = 1440;
const HEIGHT = 900;

mkdirSync(join(OUT, "shots"), { recursive: true });

const scenes = [];
const failures = [];
const consoleLines = [];
let t0 = 0;
const now = () => Date.now() - t0;

/** Records an assertion against the current scene; never throws (the video keeps rolling). */
const check = (scene, label, ok, detail = "") => {
  scene.checks.push({ label, ok, detail });
  if (!ok) failures.push(`${scene.id}: ${label}${detail ? ` — ${detail}` : ""}`);
  console.log(`   ${ok ? "PASS" : "FAIL"}  ${label}${detail ? ` (${detail})` : ""}`);
};

const scene = async (id, title, caption, body) => {
  const s = { id, title, caption, startMs: now(), checks: [] };
  console.log(`\n[scene] ${id} — ${title}`);
  try {
    await body(s);
  } catch (error) {
    check(s, "scene completed without throwing", false, String(error).slice(0, 300));
  }
  s.endMs = now();
  s.ok = s.checks.every((c) => c.ok);
  scenes.push(s);
  return s;
};

/**
 * Perspective's Datagrid plugin renders its <td>s inside a shadow root, so a plain
 * document query can't see them. Walk every open shadow root and collect the grid cells.
 */
const GRID_PROBE = `(() => {
  const cells = [];
  const headers = [];
  const walk = (root) => {
    for (const td of root.querySelectorAll("td")) {
      cells.push({ text: td.textContent, band: td.classList.contains("extractions-grid__band"), linkable: td.classList.contains("extractions-grid__linkable") });
    }
    for (const th of root.querySelectorAll("th")) headers.push(th.textContent);
    for (const el of root.querySelectorAll("*")) if (el.shadowRoot) walk(el.shadowRoot);
  };
  walk(document);
  return { cells, headers };
})()`;

const grid = (page) => page.evaluate(GRID_PROBE);

const settle = async (page, ms) => page.waitForTimeout(ms);

const main = async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    recordVideo: { dir: join(OUT, "video"), size: { width: WIDTH, height: HEIGHT } },
    deviceScaleFactor: 1,
  });

  // Headless chromium never paints a cursor into the recording; draw one so scrolls and
  // clicks are legible in the demo.
  await context.addInitScript(() => {
    const install = () => {
      // The Nuxt devtools anchor is dev-server furniture, not part of the feature.
      const hide = document.createElement("style");
      hide.textContent = '[id^="nuxt-devtools"], .nuxt-devtools-anchor { display: none !important; }';
      document.documentElement.appendChild(hide);

      const dot = document.createElement("div");
      dot.style.cssText =
        "position:fixed;z-index:2147483647;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;" +
        "background:rgba(255,103,0,.85);box-shadow:0 0 0 3px rgba(255,103,0,.25);pointer-events:none;" +
        "left:-100px;top:-100px;transition:none";
      document.documentElement.appendChild(dot);
      addEventListener("mousemove", (e) => {
        dot.style.left = `${e.clientX}px`;
        dot.style.top = `${e.clientY}px`;
      }, true);
      addEventListener("mousedown", () => (dot.style.background = "rgba(255,103,0,1)"), true);
      addEventListener("mouseup", () => (dot.style.background = "rgba(255,103,0,.85)"), true);
    };
    if (document.documentElement) install();
    else addEventListener("DOMContentLoaded", install);
  });

  const page = await context.newPage();
  t0 = Date.now();
  page.on("console", (m) => consoleLines.push(`[${m.type()}] ${m.text()}`));
  page.on("pageerror", (e) => consoleLines.push(`[pageerror] ${e.message}`));

  const shot = (s) => page.screenshot({ path: join(OUT, "shots", `${s.id}.png`) }).catch(() => {});

  // ── 1. Sign in through the real UI (bearer token, no mocks) ────────────────────────
  await scene("01-signin", "Sign in", "Real backend, real bearer token — no network mocks", async (s) => {
    await page.goto(`${BASE}/sign-in`);
    await page.getByLabel("Username").fill("extralit");
    await settle(page, 400);
    await page.getByLabel("Password").fill("12345678");
    await settle(page, 400);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await page.waitForURL((u) => !u.pathname.startsWith("/sign-in"), { timeout: 30000 });
    check(s, "signed in and left /sign-in", !page.url().includes("/sign-in"), page.url());
    await settle(page, 800);
    await shot(s);
  });

  // ── 2. The workspace-wide extraction table ─────────────────────────────────────────
  let projectionStatus = 0;
  await scene(
    "02-grid",
    "One table for the whole workspace",
    "8 references × 3 schemas, denormalized server-side into one flat grid",
    async (s) => {
      const wait = page.waitForResponse(
        (r) => r.url().includes("/api/v2/projection") && !r.url().includes("/references/") && r.request().method() === "GET",
        { timeout: 30000 }
      );
      await page.goto(`${BASE}/extractions?workspace_id=${SEED.workspaceId}`);
      projectionStatus = (await wait).status();
      check(s, "GET /api/v2/projection returned 200", projectionStatus === 200, String(projectionStatus));
      await page.waitForSelector('[data-testid="extractions-grid"]', { timeout: 30000 });
      await settle(page, 2500); // let the WASM datagrid paint its first frame

      const { cells, headers } = await grid(page);
      check(s, "Perspective datagrid painted cells", cells.length > 0, `${cells.length} cells`);
      const headerText = headers.join("|");
      for (const col of ["study_characteristics.country", "outcomes.arms.arm", "risk_of_bias.randomization"]) {
        check(s, `column present: ${col}`, headerText.includes(col));
      }
      const text = cells.map((c) => c.text).join("|");
      check(s, "reference rows rendered", text.includes("10.1016/S0140-6736(21)01812-1"));
      // Perspective infers a numeric column from the digit-only `sample_size` values and
      // renders them grouped ("4,812"), so compare against a separator-stripped copy.
      const digits = text.replace(/,/g, "");
      check(s, "agent-suggested values rendered", text.includes("Kenya") && digits.includes("4812"));
      check(s, "layout placeholder copy is gone", !(await page.locator("body").innerText()).includes("here is the page"));
      await settle(page, 2500);
      await shot(s);
    }
  );

  // ── 3. Coalescing: a submitted human answer beats the agent suggestion ─────────────
  await scene(
    "03-coalesce",
    "Human answer beats the agent",
    "design: agent said “cohort”, a reviewer submitted “cluster-RCT” — the grid shows the human answer",
    async (s) => {
      const { cells } = await grid(page);
      const text = cells.map((c) => c.text);
      check(s, "human response value shown", text.includes("cluster-RCT"));
      // The overridden reference's agent value ("cohort") must appear nowhere in the grid:
      // no other study in the seed is a cohort study, so any hit is a coalescing regression.
      check(s, "overridden agent value absent", !text.includes("cohort"), text.filter((t) => t === "cohort").join(","));
      await settle(page, 2500);
      await shot(s);
    }
  );

  // ── 4. Coverage gaps: a schema nobody has annotated still gets columns ─────────────
  await scene(
    "04-gaps",
    "Coverage gaps are visible",
    "risk_of_bias has questions but zero records — the columns still render, empty",
    async (s) => {
      const { headers } = await grid(page);
      const headerText = headers.join("|");
      check(s, "risk_of_bias.randomization column present", headerText.includes("risk_of_bias.randomization"));
      check(s, "risk_of_bias.blinding column present", headerText.includes("risk_of_bias.blinding"));
      // Hole in the data: 10.1093/cid/ciab1049 has no sample_size suggestion, and
      // 10.4269/ajtmh.22-0417 has no country — those cells must be blank, not fabricated.
      const { cells } = await grid(page);
      const blanks = cells.filter((c) => !c.text || !c.text.trim()).length;
      check(s, "blank cells rendered for missing extractions", blanks > 0, `${blanks} blank cells`);
      await settle(page, 2500);
      await shot(s);
    }
  );

  // ── 5. Table fan-out + reference banding, and banding survives virtualized scroll ──
  await scene(
    "05-banding",
    "Trial arms fan out, references stay grouped",
    "A table question stacks one row per arm; alternating bands keep each reference readable",
    async (s) => {
      const before = await grid(page);
      check(s, "row banding applied", before.cells.some((c) => c.band), `${before.cells.filter((c) => c.band).length} banded cells`);
      check(s, "linkable cells carry the pointer affordance", before.cells.some((c) => c.linkable));
      const armText = before.cells.map((c) => c.text).join("|");
      check(s, "table fan-out rows rendered", armText.includes("ITN + IRS") && armText.includes("ITN only"));

      // Scroll: regular-table recycles <td>s, so the style listener must re-apply banding.
      const box = await page.locator('[data-testid="extractions-grid"]').boundingBox();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
      await settle(page, 400);
      for (let i = 0; i < 6; i++) {
        await page.mouse.wheel(0, 120);
        await settle(page, 300);
      }
      await settle(page, 1200);
      const after = await grid(page);
      check(s, "banding survives the virtualized redraw", after.cells.some((c) => c.band));
      await shot(s);
      for (let i = 0; i < 6; i++) {
        await page.mouse.wheel(0, -120);
        await settle(page, 200);
      }
      await settle(page, 800);
    }
  );

  // ── 6. Cell click plumbing (annotation deep-link is feature-flagged off) ───────────
  await scene(
    "06-click",
    "Cells are click-addressable",
    "Each cell resolves back to its reference + schema — the annotation deep-link is flagged off for now",
    async (s) => {
      const urlBefore = page.url();
      const box = await page.locator('[data-testid="extractions-grid"]').boundingBox();
      await page.mouse.move(box.x + 300, box.y + 120, { steps: 20 });
      await settle(page, 600);
      await page.mouse.click(box.x + 300, box.y + 120);
      await settle(page, 1200);
      check(s, "click did not navigate (deep-link flag off)", page.url() === urlBefore, page.url());
      check(s, "grid still mounted after click", (await page.locator('[data-testid="extractions-grid"]').count()) === 1);
      await shot(s);
      await settle(page, 1200);
    }
  );

  // ── 7. Swapping workspace reloads the projection in place ─────────────────────────
  await scene(
    "07-swap",
    "Switching workspace swaps the projection",
    "A different workspace ⇒ a different column manifest, loaded into the same grid",
    async (s) => {
      const wait = page.waitForResponse(
        (r) => r.url().includes("/api/v2/projection") && r.request().method() === "GET",
        { timeout: 30000 }
      );
      await page.goto(`${BASE}/extractions?workspace_id=${E2E_SEED.workspaceId}`);
      check(s, "projection refetched for the new workspace", (await wait).status() === 200);
      await page.waitForSelector('[data-testid="extractions-grid"]', { timeout: 30000 });
      await settle(page, 2500);
      const { headers, cells } = await grid(page);
      const headerText = headers.join("|");
      check(s, "new workspace's columns rendered", headerText.includes(`${E2E_SEED.schemaName}.size`), headerText.slice(0, 200));
      check(s, "previous workspace's columns are gone", !headerText.includes("outcomes.arms.arm"));
      check(s, "new workspace's rows rendered", cells.map((c) => c.text).join("|").includes(E2E_SEED.reference));
      await settle(page, 2000);
      await shot(s);
    }
  );

  // ── 8. Empty workspace ────────────────────────────────────────────────────────────
  await scene(
    "08-empty",
    "An un-extracted workspace says so",
    "No schemas, no records — an explicit empty state, not a blank grid",
    async (s) => {
      await page.goto(`${BASE}/extractions?workspace_id=${SEED.emptyWorkspaceId}`);
      await settle(page, 3000);
      const body = await page.locator("body").innerText();
      check(s, "empty state message rendered", /no extracted|empty|nothing/i.test(body), body.replace(/\s+/g, " ").slice(0, 160));
      check(s, "no grid element mounted", (await page.locator('[data-testid="extractions-grid"]').count()) === 0);
      await settle(page, 1500);
      await shot(s);
    }
  );

  // ── 9. Back to the demo workspace for the closing frame ────────────────────────────
  await scene("09-final", "Back to the extraction table", "One workspace-wide view of everything extracted so far", async (s) => {
    await page.goto(`${BASE}/extractions?workspace_id=${SEED.workspaceId}`);
    await page.waitForSelector('[data-testid="extractions-grid"]', { timeout: 30000 });
    await settle(page, 3000);
    const { cells } = await grid(page);
    check(s, "grid re-renders after navigating back", cells.length > 0, `${cells.length} cells`);
    await shot(s);
    await settle(page, 2000);
  });

  const durationMs = now();
  await page.close();
  await context.close();
  await browser.close();

  const pageErrors = consoleLines.filter((l) => l.startsWith("[pageerror]"));
  const consoleErrors = consoleLines.filter((l) => l.startsWith("[error]"));
  // Only errors this demo owns gate the run. The harness drives `npm run dev`, so Nuxt
  // devtools, HMR and third-party libraries all log on the same `[error]` channel — treating
  // every one as fatal would fail the pipeline on unrelated dev-server noise, and the only
  // remedy would be switching off the very signal the gate exists for. `pageerror` needs no
  // such filter because an uncaught app exception is unambiguous.
  const OWNED_CONSOLE_ERROR = /^\[error\] \[(ExtractionsGrid|grid-adapter)\]/;
  const ownedConsoleErrors = consoleErrors.filter((l) => OWNED_CONSOLE_ERROR.test(l));

  writeFileSync(join(OUT, "console.log"), consoleLines.join("\n"));
  writeFileSync(
    join(OUT, "timeline.json"),
    JSON.stringify(
      {
        durationMs,
        width: WIDTH,
        height: HEIGHT,
        scenes,
        pageErrors,
        consoleErrors,
        ownedConsoleErrors,
        totalChecks: scenes.reduce((n, s) => n + s.checks.length, 0),
        failures,
      },
      null,
      2
    )
  );

  console.log(`\n${scenes.reduce((n, s) => n + s.checks.length, 0)} checks, ${failures.length} failed`);
  if (pageErrors.length) console.log(`page errors:\n${pageErrors.join("\n")}`);
  // All console errors are reported (dev-server noise is still worth seeing in the log), but
  // the owned subset is called out separately because only it can fail the run.
  if (consoleErrors.length) console.log(`console errors:\n${consoleErrors.join("\n")}`);
  if (ownedConsoleErrors.length) console.log(`app console errors:\n${ownedConsoleErrors.join("\n")}`);
  if (failures.length) {
    console.log(`FAILURES:\n${failures.join("\n")}`);
  }
  // An uncaught exception in the app is the most severe class of runtime breakage, and every
  // scene assertion can still pass around it — so gating the exit code on `failures` alone
  // would let a `pageerror` produce a green "N/N checks passed" video and a zero exit,
  // exactly the "broken UI dressed up as a finished video" this harness exists to prevent.
  // `DEMO_ALLOW_PAGE_ERRORS=1` is the explicit opt-out for known-benign noise.
  const allowPageErrors = process.env.DEMO_ALLOW_PAGE_ERRORS === "1";
  if (pageErrors.length && !allowPageErrors) {
    console.log(`page errors are fatal (set DEMO_ALLOW_PAGE_ERRORS=1 to override)`);
  }
  // Owned `console.error`s get the same treatment, and for the same reason: the component this
  // harness demos reports its worst failure that way — ExtractionsGrid logs
  // "[ExtractionsGrid] failed to build the Perspective table…" and emits `load-error` rather
  // than throwing — so an empty grid would sail past scene checks that don't count cells.
  // Collecting these into `timeline.json` and the Outro while leaving them unable to fail the
  // run made them read as a gated signal they weren't.
  const allowConsoleErrors = process.env.DEMO_ALLOW_CONSOLE_ERRORS === "1";
  if (ownedConsoleErrors.length && !allowConsoleErrors) {
    console.log(`app console errors are fatal (set DEMO_ALLOW_CONSOLE_ERRORS=1 to override)`);
  }
  if (
    failures.length ||
    (pageErrors.length && !allowPageErrors) ||
    (ownedConsoleErrors.length && !allowConsoleErrors)
  ) {
    process.exitCode = 1;
  }
};

await main();
