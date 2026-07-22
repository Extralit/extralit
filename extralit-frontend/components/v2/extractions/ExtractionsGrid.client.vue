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
 * tearing down `previousTable` (the table this call is replacing, if any) once it is safe
 * to do so.
 *
 * Ordering: `viewer.load(newTable)` is documented (see
 * `@perspective-dev/viewer/dist/wasm/perspective-viewer.d.ts`, `load()`) as equivalent to
 * `restore({ table: newTable.get_name() })` and resolving only once "the first frame ...
 * is guaranteed to have been drawn" — i.e. by the time it resolves the viewer is bound to
 * `newTable` and no longer references `previousTable`. That makes `previousTable.delete()`
 * safe immediately after `load()` (and the `restore()` that reasserts the Datagrid plugin
 * config) resolve, without ever calling `viewer.delete()` — unlike full unmount, this path
 * replaces the bound table on a *live* viewer, it does not tear the viewer down.
 */
async function loadProjectionIntoViewer(
  projection: WorkspaceProjection,
  previousTable: PerspectiveTableLike | null
): Promise<void> {
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
  table = newTable;

  const viewer = viewerEl.value;
  if (!viewer?.load) {
    // happy-dom never upgrades the custom element, so `load` stays undefined there — this
    // guard is what keeps the unit test from touching the untestable Perspective wiring.
    return;
  }

  try {
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

    // The viewer is now bound to `newTable`; `previousTable` (if any) is unreferenced.
    await safeDelete(previousTable);

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
    // escape as an unhandled rejection.
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
  await loadProjectionIntoViewer(props.projection, null);
});

watch(
  () => props.projection,
  async (nextProjection) => {
    if (cancelled || !client) {
      return;
    }
    bandByRow = bandParity(nextProjection);
    const previousTable = table;
    await loadProjectionIntoViewer(nextProjection, previousTable);
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
