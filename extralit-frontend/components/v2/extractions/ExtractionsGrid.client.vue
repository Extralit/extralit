<template>
  <perspective-viewer ref="viewerEl" class="extractions-grid" data-testid="extractions-grid" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { type HTMLPerspectiveViewerElement } from "@perspective-dev/viewer";
import { initPerspectiveClient } from "~/components/v2/extractions/perspective-bootstrap";
import { type WorkspaceProjection } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { toPerspectiveData, bandParity } from "~/v2/domain/entities/projection/grid-adapter";

/**
 * Vue wrapper around `<perspective-viewer>` (§3.1/§3.3 extraction grid). The `.client.vue`
 * suffix stops Nuxt from ever SSR-evaluating this file: perspective-viewer/-datagrid boot
 * WASM + a Web Component the moment they're imported, which only exists client-side.
 *
 * Loads the flat projection into a static Datagrid (no sort/group/filter — natural
 * insertion order, toolbar hidden), reloading the underlying Perspective table whenever
 * `props.projection` changes (the host page swaps workspaces without remounting this
 * component).
 *
 * The grid is read-only: its one DOM-level addition is reference-group row banding
 * (`bandParity`), which Perspective has no concept of. It is re-applied on every
 * `addStyleListener` draw because virtualized `<td>`s are recycled and never retain classes
 * across redraws. Cells are deliberately not clickable — navigating from a cell to v1
 * annotation-mode is future work, and shipping the plumbing behind an always-off guard only
 * created dead code.
 */

interface CellMeta {
  type: string;
  y?: number;
}

interface RegularTableLike extends HTMLElement {
  addStyleListener(listener: (event: { detail: RegularTableLike }) => void | Promise<void>): () => void;
  getMeta(element?: HTMLElement): CellMeta | undefined;
}

interface PerspectiveTableLike {
  delete: () => Promise<unknown>;
}

interface PerspectiveClientLike {
  table: (data: Record<string, unknown>[]) => Promise<PerspectiveTableLike>;
}

const props = defineProps<{ projection: WorkspaceProjection }>();

const emit = defineEmits<{
  // Fired when building/loading a Perspective table for the current projection fails (e.g.
  // `client.table()` rejects). The host page maps this onto its existing `loadError` state
  // so a rejection here can never again leave the user staring at a blank, unexplained
  // <perspective-viewer> (see `performLoad`'s doc comment).
  "load-error": [];
}>();

const viewerEl = ref<HTMLPerspectiveViewerElement | null>(null);

// Reference-group row banding is a pure function of the projection: recomputed whenever
// `props.projection` changes so it never lags behind the rows currently on screen.
let bandByRow: number[] = bandParity(props.projection);

let client: PerspectiveClientLike | null = null;
let table: PerspectiveTableLike | null = null;
let regularTable: RegularTableLike | null = null;
let unsubscribeStyle: (() => void) | null = null;

// Flipped by onBeforeUnmount and checked after every await on the mount/reload path: the
// perspective boot chain (`initPerspectiveClient` → `table`) is async, and a fast
// route navigation can unmount this component while it's still in flight. Without this
// guard, a `table` created after cleanup already ran would never get `.delete()`d — a
// WASM-heap leak — and post-await calls into a detached viewer could throw as an
// unhandled rejection.
let cancelled = false;

// Every `loadProjectionIntoViewer` call is appended to this chain instead of running
// immediately: see the doc comment above that function for why unserialized calls (mount
// racing a prop-change watcher, or watcher racing watcher) can clobber each other and leak
// tables.
let loadChain: Promise<void> = Promise.resolve();

async function safeDelete(candidate: PerspectiveTableLike | null): Promise<void> {
  if (!candidate) {
    return;
  }
  try {
    await candidate.delete();
  } catch {
    // Cleanup races (e.g. fast route navigation, or a table already released by the
    // viewer) are not actionable — swallow.
  }
}

async function deleteSupersededTable(candidate: PerspectiveTableLike | null): Promise<void> {
  if (!candidate) {
    return;
  }
  try {
    await candidate.delete();
  } catch (error) {
    // Neither `load()` nor `eject()` documents synchronously releasing the View bound to
    // the table being replaced (see the doc comment above `loadProjectionIntoViewer`), so
    // this can legitimately still throw per `Table.delete()`'s documented precondition
    // ("no View instances registered to it, which must be deleted first" —
    // `@perspective-dev/client/dist/wasm/perspective-js.d.ts`). Swallowing it here would
    // hide a leaked Table + View on every projection swap, so surface it loudly instead —
    // the grid itself keeps working either way.
    console.warn("[ExtractionsGrid] failed to delete the superseded Perspective table after a projection swap", error);
  }
}

function rowIndexAt(rt: RegularTableLike, td: HTMLElement): number | null {
  const meta = rt.getMeta(td);
  // regular-table uses a single DOM interface (HTMLTableCellElement) for both <td> and
  // <th>, and CellMetadataRowHeader carries the same required `y` shape as a body cell's
  // metadata. Without this check a row-header <th> would be misread as a body cell and
  // banded against the wrong reference group.
  if (meta?.type !== "body" || meta.y === undefined) {
    return null;
  }
  return meta.y;
}

/**
 * The one style-only affordance applied to grid `<td>`s: reference-group row banding.
 * Declared once here and reused by `ensureShadowStyles` below; the `<style scoped>` block at
 * the end of this file carries an equivalent copy for the light-DOM render target (see that
 * block's comment for why a single copy can't serve both — Vue scoped/`:deep()` styles
 * compile to a document-level stylesheet, which cannot cross a shadow boundary). Keep both
 * copies in sync if you touch either.
 */
const CELL_STYLE_RULES = "td.extractions-grid__band { background-color: rgba(0, 0, 0, 0.035); }";

const SHADOW_STYLE_ELEMENT_ID = "extractions-grid-cell-style";

/**
 * `@perspective-dev/viewer-datagrid` picks its render target with
 * `CSS.supports("selector(:host-context(foo))") ? "shadow" : "light"` and, for the shadow
 * case, renders the `regular-table` (and every `<td>`) inside an `attachShadow({mode:"open"})`
 * root. Chromium supports `:host-context`, so in the primary target browser `rt` — the same
 * element `applyCellStyles` queries via `querySelectorAll("td")` — lives inside that shadow
 * root, which document-level CSS (including this file's Vue `:deep()` rules) cannot reach.
 * This injects a plain `<style>` element straight into that root instead: scoped to the root
 * it's appended to with no `adoptedStyleSheets` feature-detection needed. No-ops for the
 * light-DOM render target (the `<style scoped>` rules already reach those cells there) and is
 * idempotent per root (id-guarded) so repeated draws/plugin swaps never append duplicates.
 */
function ensureShadowStyles(rt: RegularTableLike): void {
  const root = rt.getRootNode();
  if (!(root instanceof ShadowRoot) || root.getElementById(SHADOW_STYLE_ELEMENT_ID)) {
    return;
  }
  const style = document.createElement("style");
  style.id = SHADOW_STYLE_ELEMENT_ID;
  style.textContent = CELL_STYLE_RULES;
  root.appendChild(style);
}

function applyCellStyles(rt: RegularTableLike): void {
  const cells = rt.querySelectorAll<HTMLTableCellElement>("td");
  for (const td of Array.from(cells)) {
    const rowIndex = rowIndexAt(rt, td);
    const isBand = rowIndex !== null && bandByRow[rowIndex] === 1;
    // Re-applied every draw: virtualized <td>s are recycled and never retain classes.
    td.classList.toggle("extractions-grid__band", isBand);
  }
}

/**
 * Builds a fresh Perspective table for `projection` and installs it into the viewer,
 * tearing down the table it replaces (if any) once it is safe to do so.
 *
 * Concurrency: both `onMounted` and the `watch(() => props.projection, ...)` callback below
 * funnel through this function, and Vue does not serialize async watcher callbacks against
 * each other or against `onMounted` — two calls can be in flight simultaneously (mount vs.
 * watch, or watch vs. a second watch firing before the first's async body has finished).
 * Left unserialized, a slower call resolving after a faster, more-recently-requested one
 * would clobber the correct, just-rendered table with a stale one, and whichever table lost
 * that race would never become anyone's `previousTable` — a leaked Table + View. To prevent
 * this, every call is appended to `loadChain`: a new call's body does not start running
 * until every call requested before it has fully settled (finished a swap, or bailed out).
 * This guarantees calls run in request order, so the table for the most-recently-requested
 * `projection` is always the last thing written to the viewer, exactly one Table is ever
 * live, and each call can safely read module-scope `table` — "whatever the viewer is
 * currently bound to" — without needing it passed as a parameter.
 *
 * Table release ordering on a swap: neither `load()` nor `eject()` (see their docstrings in
 * `@perspective-dev/viewer/dist/wasm/perspective-viewer.d.ts`) documents synchronously
 * dropping the View bound to the table being replaced. `load()` only guarantees "the first
 * frame ... is guaranteed to have been drawn" — nothing about releasing a *previous*
 * binding. `Table.delete()` (`@perspective-dev/client/dist/wasm/perspective-js.d.ts`)
 * throws unless the table "has no View instances registered to it (which must be deleted
 * first)". `eject()`, however, is documented to "Restart this `<perspective-viewer>` to its
 * initial state, before `load()`" specifically so `load()` can be called again on the same
 * element — the strongest documented lever available for releasing the current binding
 * without tearing the viewer down — so it is called on the outgoing table's behalf before
 * loading its replacement. That still isn't an explicit guarantee against `Table.delete()`
 * throwing afterwards, so a rejection there is handled by `deleteSupersededTable`, not
 * silently swallowed.
 */
function loadProjectionIntoViewer(projection: WorkspaceProjection): Promise<void> {
  const run = loadChain.then(() => performLoad(projection));
  // Keep the chain usable even if this run rejects or the viewer bails out — a later,
  // already-requested call must not be stuck behind it forever. Callers that care about
  // this specific call's outcome still get it via the returned `run`.
  loadChain = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

async function performLoad(projection: WorkspaceProjection): Promise<void> {
  if (!client) {
    return;
  }

  let newTable: PerspectiveTableLike;
  try {
    // Building the table is guarded here (rather than a bare `await` before any try/catch)
    // specifically so a rejection — e.g. a non-scalar cell value `client.table()` can't
    // infer a schema for, see `toPerspectiveData` — surfaces as `load-error` instead of
    // escaping as an unhandled rejection. An unhandled rejection here previously left
    // `loadFailed` at `false` while the viewer stayed mounted empty: a silent, total
    // failure with no explanation ever shown to the user.
    newTable = await client.table(toPerspectiveData(projection));
  } catch (error) {
    // Guards against a stale load's failure clobbering a newer, healthy projection: `loadChain`
    // serializes *starts*, not *settlements* — an earlier-queued `performLoad(P1)` can still be
    // awaiting a rejecting `client.table()` after `performLoad(P2)` has already been requested
    // (and, since Vue updates `props.projection` synchronously before the watcher fires, has
    // already become the current `props.projection`). Without this check, P1's rejection would
    // still emit `load-error`, which the page latches into a permanent `loadFailed` state that
    // outlives P2's perfectly healthy load — see this file's `load-error` doc comment and the
    // fix's changelog entry for the full failure sequence.
    if (!cancelled && projection === props.projection) {
      console.error("[ExtractionsGrid] failed to build the Perspective table for this projection", error);
      emit("load-error");
    }
    return;
  }
  if (cancelled) {
    // Unmount already ran and, finding nothing to clean up at the time, will never run
    // again — this table would otherwise never be deleted.
    await safeDelete(newTable);
    return;
  }

  // Safe to read fresh here: by construction (see the doc comment above
  // `loadProjectionIntoViewer`) no other call is running concurrently, so this is exactly
  // the table the viewer is currently bound to (or `null` on the very first load).
  const previousTable = table;
  table = newTable;
  // Distinguishes "a path already released `previousTable`" from "an await inside the `try`
  // below threw before any path got the chance to". Only the assignment immediately after
  // `deleteSupersededTable` in the normal (non-cancelled) path is actually observed: it is
  // followed by more code in that same `try` (the `getPlugin` await, `addStyleListener`)
  // that can still throw into the `catch`, which reads this flag to avoid
  // deleting `previousTable` a second time. Every `if (cancelled)` branch inside the `try`
  // `return`s immediately after its own delete — control can never fall from a `return` into
  // this function's `catch` — so a flag write there would have no observer; those are not
  // written. The same reasoning applies below: the release for the `!viewer?.load` early
  // return happens before the `try` even begins, so nothing ever reads a flag for it either.
  let previousTableDeleted = false;

  const viewer = viewerEl.value;
  if (!viewer?.load) {
    // happy-dom never upgrades the custom element, so `load` stays undefined there — this
    // guard is what keeps the unit test from touching the untestable Perspective wiring. It's
    // also a real, deterministic path in production whenever the viewer hasn't upgraded yet
    // by the time a projection swap lands: `table = newTable` above already dropped the last
    // reference to `previousTable`, so it must be released here or it leaks permanently.
    await deleteSupersededTable(previousTable);
    return;
  }

  try {
    if (previousTable && viewer.eject) {
      // Release the viewer's current View/Table binding before loading the replacement —
      // see the doc comment above `loadProjectionIntoViewer` for why this, and not just
      // `load()`, is what makes the delete below safe.
      await viewer.eject();
      if (cancelled) {
        await safeDelete(previousTable);
        return;
      }
    }

    await viewer.load(newTable);
    if (cancelled) {
      await safeDelete(previousTable);
      return;
    }
    // Static grid: no config/settings panel, natural (insertion) order — no `sort`.
    await viewer.restore({ plugin: "Datagrid", settings: false });
    if (cancelled) {
      await safeDelete(previousTable);
      return;
    }

    await deleteSupersededTable(previousTable);
    previousTableDeleted = true;

    unsubscribeStyle?.();
    unsubscribeStyle = null;
    const plugin = await viewer.getPlugin?.("Datagrid");
    if (cancelled) {
      return;
    }
    regularTable = (plugin?.regular_table as RegularTableLike | undefined) ?? null;
    if (regularTable) {
      ensureShadowStyles(regularTable);
      unsubscribeStyle = regularTable.addStyleListener((styleEvent) => applyCellStyles(styleEvent.detail));
      // `addStyleListener` only pushes onto regular-table's listener array — it neither invokes
      // the callback nor forces a redraw (see `addStyleListener` in
      // `node_modules/regular-table/dist/esm/regular-table.js`). `viewer.load()` above already
      // guarantees "the first frame ... has been drawn", so that first frame happened before we
      // registered and our listener missed it: without this call the banding classes are
      // absent until something else triggers a redraw (a scroll or a resize), i.e. never,
      // for a user who just reads the grid.
      applyCellStyles(regularTable);
    }
  } catch (error) {
    // A viewer detached mid-flight (fast route navigation, or torn down by onBeforeUnmount
    // while this chain was still in progress) throws here too, alongside genuine failures
    // from `eject()`/`load()`/`restore()`/`getPlugin()` (an unrenderable schema, a rejected
    // `restore` config, a plugin regression). `previousTable` is still this call's
    // responsibility either way: none of the `cancelled` branches above ran (they return
    // instead of throwing), so unless the normal swap already deleted it, it would otherwise
    // leak.
    if (previousTable && !previousTableDeleted) {
      await deleteSupersededTable(previousTable);
    }
    // Mirrors the `client.table()` catch above: only report if this call is both live (not
    // unmounted) and still current (not a superseded projection's failure racing in after a
    // newer, healthy one already took over) — see that catch's doc comment for the full
    // staleness-race rationale. Without this, a viewer/plugin failure here left `loadFailed`
    // at `false` while the viewer stayed mounted empty — the exact silent-failure mode the
    // `load-error` contract exists to eliminate.
    if (!cancelled && projection === props.projection) {
      console.error("[ExtractionsGrid] failed to load the Perspective table into the viewer", error);
      emit("load-error");
    }
  }
}

onMounted(async () => {
  // `initPerspectiveClient` hoists the Perspective `Client` (and its Web Worker + WASM
  // heap) into a module-level memo shared across every mount — see the doc comment on
  // `initPerspectiveClient` in perspective-bootstrap.ts for why this component must never
  // call `perspective.worker()` directly.
  client = await initPerspectiveClient();
  if (cancelled) {
    return;
  }
  // Read `props.projection` fresh (not a captured value) in case it changed while the
  // above awaited.
  await loadProjectionIntoViewer(props.projection);
});

watch(
  () => props.projection,
  async (nextProjection) => {
    if (cancelled || !client) {
      return;
    }
    bandByRow = bandParity(nextProjection);
    await loadProjectionIntoViewer(nextProjection);
  }
);

onBeforeUnmount(async () => {
  cancelled = true;
  const viewer = viewerEl.value;
  unsubscribeStyle?.();
  unsubscribeStyle = null;
  regularTable = null;

  // Order matters: a table still referenced by a live viewer throws on delete().
  try {
    await viewer?.delete?.();
  } catch {
    // Cleanup races (e.g. fast route navigation) are not actionable — swallow.
  }
  await safeDelete(table);
  table = null;
  // Intentionally NOT `client.terminate()`d here: `client` is the module-level Client
  // shared across every mount (see `initPerspectiveClient`'s doc comment) and outlives this
  // component instance by design — terminating it would tear down the one shared Worker for
  // every other still- or future-mounted grid too. Only the local reference is dropped.
  client = null;
});
</script>

<style scoped lang="scss">
.extractions-grid {
  display: block;
  width: 100%;
  height: calc(100vh - 160px);
}

// Reaches the grid's <td>s only for the "light" Perspective Datagrid render target — a
// ShadowRoot render target (the common one in Chromium; see `ensureShadowStyles` in the
// <script> block above) is outside any document-level stylesheet's reach, so these rules are
// duplicated there via a directly-injected <style> element. Keep both copies in sync.
:deep(td.extractions-grid__band) {
  background-color: rgba(0, 0, 0, 0.035);
}
</style>
