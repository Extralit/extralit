<template>
  <perspective-viewer ref="viewerEl" class="extractions-grid" data-testid="extractions-grid" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { type HTMLPerspectiveViewerElement } from "@perspective-dev/viewer";
import { initPerspective } from "~/components/v2/extractions/perspective-bootstrap";
import { type WorkspaceProjection, type ProjectionGridCell } from "~/v2/domain/entities/projection/WorkspaceProjection";
import { toPerspectiveData, cellAt, bandParity } from "~/v2/domain/entities/projection/grid-adapter";

/**
 * Vue wrapper around `<perspective-viewer>` (§3.1/§3.3 extraction grid). The `.client.vue`
 * suffix stops Nuxt from ever SSR-evaluating this file: perspective-viewer/-datagrid boot
 * WASM + a Web Component the moment they're imported, which only exists client-side.
 *
 * Loads the flat projection once into a static Datagrid (no sort/group/filter — natural
 * insertion order, toolbar hidden), then layers two DOM-only affordances on top of the
 * plugin's `regular-table` since Perspective itself has no concept of either:
 *  - reference-group row banding (`bandParity`), re-applied on every `addStyleListener` draw
 *    because virtualized `<td>`s are recycled and never retain classes across redraws.
 *  - a single `click` listener on the viewer host, resolved through `event.composedPath()`
 *    so it still finds the cell whether the datagrid plugin rendered into shadow or light DOM.
 */

interface CellMeta {
  type?: string;
  y?: number;
  column_header?: Array<string | HTMLElement>;
}

interface RegularTableLike extends HTMLElement {
  addStyleListener(listener: (event: { detail: RegularTableLike }) => void | Promise<void>): () => void;
  getMeta(element?: HTMLElement): CellMeta | undefined;
}

const props = defineProps<{ projection: WorkspaceProjection }>();

const emit = defineEmits<{
  "cell-click": [payload: { cell: ProjectionGridCell; reference: string; schemaId: string; columnName: string }];
}>();

const viewerEl = ref<HTMLPerspectiveViewerElement | null>(null);

// Computed once: the projection is loaded a single time and never re-sorted/re-filtered in
// this static grid, so the parity-per-row-index table stays valid for the component's lifetime.
const bandByRow = bandParity(props.projection);

let table: { delete: () => Promise<unknown> } | null = null;
let regularTable: RegularTableLike | null = null;
let unsubscribeStyle: (() => void) | null = null;

function cellMetaAt(rt: RegularTableLike, td: HTMLElement): { rowIndex: number; columnName: string } | null {
  const meta = rt.getMeta(td);
  const rowIndex = meta?.y;
  const header = meta?.column_header;
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
  const td = event.composedPath().find((node): node is HTMLTableCellElement => node instanceof HTMLTableCellElement);
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

onMounted(async () => {
  const perspective = await initPerspective();
  const client = await perspective.worker();
  table = await client.table(toPerspectiveData(props.projection));

  // happy-dom never upgrades the custom element, so `load` stays undefined there — this
  // guard is what keeps the unit test from touching the untestable Perspective wiring below.
  const viewer = viewerEl.value;
  if (!viewer?.load) {
    return;
  }

  await viewer.load(table);
  // Static grid: no config/settings panel, natural (insertion) order — no `sort`.
  await viewer.restore({ plugin: "Datagrid", settings: false });

  const plugin = await viewer.getPlugin?.("Datagrid");
  regularTable = (plugin?.regular_table as RegularTableLike | undefined) ?? null;
  if (regularTable) {
    unsubscribeStyle = regularTable.addStyleListener((styleEvent) => applyCellStyles(styleEvent.detail));
  }

  viewer.addEventListener?.("click", handleClick);
});

onBeforeUnmount(async () => {
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
  try {
    await table?.delete();
  } catch {
    // Same rationale as above.
  }
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
