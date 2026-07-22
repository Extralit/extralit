<template>
  <perspective-viewer ref="viewerEl" class="extractions-grid" data-testid="extractions-grid" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { type HTMLPerspectiveViewerElement } from "@perspective-dev/viewer";
import { initPerspective } from "~/components/v2/extractions/perspective-bootstrap";
import { type WorkspaceProjection, type ProjectionGridCell } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { toPerspectiveData, cellAt, bandParity } from "~/v2/domain/entities/projection/grid-adapter";

/**
 * Vue wrapper around `<perspective-viewer>` (§3.1/§3.3 extraction grid). The `.client.vue`
 * suffix stops Nuxt from ever SSR-evaluating this file: perspective-viewer/-datagrid boot
 * WASM + a Web Component the moment they're imported, which only exists client-side.
 *
 * Loads the flat projection into a static Datagrid (no sort/group/filter — natural
 * insertion order, toolbar hidden), reloading the underlying Perspective table whenever
 * `props.projection` changes (the host page swaps workspaces without remounting this
 * component). Layers two DOM-only affordances on top of the plugin's `regular-table` since
 * Perspective itself has no concept of either:
 *  - reference-group row banding (`bandParity`), re-applied on every `addStyleListener` draw
 *    because virtualized `<td>`s are recycled and never retain classes across redraws.
 *  - a single `click` listener on the viewer host, resolved through `event.composedPath()`
 *    so it still finds the cell whether the datagrid plugin rendered into shadow or light DOM.
 */

interface CellMeta {
  type: string;
  y?: number;
  column_header?: Array<string | HTMLElement>;
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
  "cell-click": [payload: { cell: ProjectionGridCell; reference: string; schemaId: string; columnName: string }];
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
// perspective boot chain (`initPerspective` → `worker` → `table`) is async, and a fast
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

function cellMetaAt(rt: RegularTableLike, td: HTMLElement): { rowIndex: number; columnName: string } | null {
  const meta = rt.getMeta(td);
  // regular-table uses a single DOM interface (HTMLTableCellElement) for both <td> and
  // <th>, and CellMetadataRowHeader carries the same required `y` + `column_header` shape
  // as a body cell's metadata. Without this check a row-header <th> can pass the rest of
  // the guard below and be misread as a body cell.
  if (meta?.type !== "body") {
    return null;
  }
  const rowIndex = meta.y;
  const header = meta.column_header;
  const columnName = header && header.length > 0 ? header[header.length - 1] : undefined;
  if (rowIndex === undefined || typeof columnName !== "string") {
    return null;
  }
  return { rowIndex, columnName };
}

function applyCellStyles(rt: RegularTableLike): void {
  const cells = rt.querySelectorAll<HTMLTableCellElement>("td");
  for (const td of Array.from(cells)) {
    const at = cellMetaAt(rt, td);
    const isBand = at !== null && bandByRow[at.rowIndex] === 1;
    const isLinkable = at !== null && cellAt(props.projection, at.rowIndex, at.columnName) !== null;
    // Re-applied every draw: virtualized <td>s are recycled and never retain classes.
    td.classList.toggle("extractions-grid__band", isBand);
    td.classList.toggle("extractions-grid__linkable", isLinkable);
  }
}

function handleClick(event: Event): void {
  if (!regularTable) {
    return;
  }
  // Restrict the lookup to <td> (matching what applyCellStyles already scopes to via
  // querySelectorAll("td")) so a click that resolves to a row-header <th> can't even reach
  // cellMetaAt's guard.
  const td = event
    .composedPath()
    .find((node): node is HTMLTableCellElement => node instanceof HTMLTableCellElement && node.tagName === "TD");
  if (!td) {
    return;
  }
  const at = cellMetaAt(regularTable, td);
  if (!at) {
    return;
  }
  const cell = cellAt(props.projection, at.rowIndex, at.columnName);
  const row = props.projection.rows[at.rowIndex];
  const column = props.projection.columns.find((candidate) => candidate.name === at.columnName);
  if (!cell || !row || !column) {
    return;
  }
  emit("cell-click", { cell, reference: row.reference, schemaId: column.schemaId, columnName: at.columnName });
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
  const newTable = await client.table(toPerspectiveData(projection));
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
  // Tracks whether `previousTable` has already been handed to a delete call on one of the
  // `cancelled` early-return paths below, so the catch block (which can be reached after any
  // of those same awaits throws instead of merely observing `cancelled`) never deletes it a
  // second time.
  let previousTableDeleted = false;

  const viewer = viewerEl.value;
  if (!viewer?.load) {
    // happy-dom never upgrades the custom element, so `load` stays undefined there — this
    // guard is what keeps the unit test from touching the untestable Perspective wiring.
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
        previousTableDeleted = true;
        return;
      }
    }

    await viewer.load(newTable);
    if (cancelled) {
      await safeDelete(previousTable);
      previousTableDeleted = true;
      return;
    }
    // Static grid: no config/settings panel, natural (insertion) order — no `sort`.
    await viewer.restore({ plugin: "Datagrid", settings: false });
    if (cancelled) {
      await safeDelete(previousTable);
      previousTableDeleted = true;
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
      unsubscribeStyle = regularTable.addStyleListener((styleEvent) => applyCellStyles(styleEvent.detail));
    }

    // Idempotent: addEventListener silently ignores a re-registration of the exact same
    // (type, listener) pair, so calling this again on reload does not double-fire clicks.
    viewer.addEventListener?.("click", handleClick);
  } catch {
    // A viewer detached mid-flight (fast route navigation, or torn down by onBeforeUnmount
    // while this chain was still in progress) throws here — not actionable, and must not
    // escape as an unhandled rejection. `previousTable`, however, is still this call's
    // responsibility: none of the `cancelled` branches above ran (they return instead of
    // throwing), so unless the normal swap already deleted it, it would otherwise leak.
    if (previousTable && !previousTableDeleted) {
      await deleteSupersededTable(previousTable);
    }
  }
}

onMounted(async () => {
  const perspective = await initPerspective();
  if (cancelled) {
    return;
  }
  client = await perspective.worker();
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
  viewer?.removeEventListener?.("click", handleClick);
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
});
</script>

<style scoped lang="scss">
.extractions-grid {
  display: block;
  width: 100%;
  height: calc(100vh - 160px);
}

:deep(td.extractions-grid__band) {
  background-color: rgba(0, 0, 0, 0.035);
}

:deep(td.extractions-grid__linkable) {
  cursor: pointer;
}
</style>
