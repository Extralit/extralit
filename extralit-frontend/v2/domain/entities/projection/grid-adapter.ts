import { type WorkspaceProjection, type ProjectionGridCell } from "./WorkspaceProjection";

/**
 * Flat-row column name carrying the reference (DOI/identifier) for each row.
 * Kept out of `projection.columns` since it is a manifest-independent, always-present key.
 */
export const REFERENCE_COLUMN = "reference";

/**
 * Maps a `WorkspaceProjection` into the flat-row shape Perspective ingests.
 *
 * `projection.columns` order is the single source of truth for column order (server-side
 * question order is definition order, not alphabetical). We iterate `columns` to build each
 * record rather than relying on the emitted plain object's own key insertion order for
 * anything downstream: today every column name is `Schema.question[.subcol]` and always
 * contains a `.`, so it can never collide with JS's canonical-integer-key hoisting (e.g. a
 * bare `"2024"` key would sort before string keys) — but that safety is a property of the
 * naming convention, not of this function's return type. A plain `Record<string, unknown>`
 * has no ordering guarantee Perspective is contractually bound to respect. Handoff note for
 * Phase 2: prefer passing `projection.columns` as Perspective's explicit column/schema
 * config rather than relying on inferred key order from the objects returned here.
 * `reference` is emitted first so every row shares an identical, stably-ordered key set —
 * every manifest column is present on every row (`null` when the cell is absent) so
 * Perspective infers one stable schema instead of a per-row-varying one.
 */
export function toPerspectiveData(projection: WorkspaceProjection): Record<string, unknown>[] {
  return projection.rows.map((row) => {
    const record: Record<string, unknown> = { [REFERENCE_COLUMN]: row.reference };
    for (const column of projection.columns) {
      const cell = row.cells[column.name];
      record[column.name] = cell ? cell.value : null;
    }
    return record;
  });
}

/**
 * Looks up the enriched cell (value + provenance) for a grid position.
 *
 * Relies on the static-grid invariant: the projection is loaded once, unsorted and
 * unfiltered, so a datagrid row index maps 1:1 onto `projection.rows` by array position.
 * Returns null for an absent cell or an out-of-range row index.
 */
export function cellAt(
  projection: WorkspaceProjection,
  rowIndex: number,
  columnName: string
): ProjectionGridCell | null {
  const row = projection.rows[rowIndex];
  if (!row) {
    return null;
  }
  return row.cells[columnName] ?? null;
}

/**
 * Returns a 0/1 parity value per row that flips whenever `reference` changes from the
 * previous row (not per row). Perspective has no notion of merged/grouped cells, so this
 * alternating band is the §3.1 reference-grouping affordance rendered as a background tint.
 */
export function bandParity(projection: WorkspaceProjection): number[] {
  let parity = 0;
  let previousReference: string | null = null;
  return projection.rows.map((row) => {
    if (previousReference !== null && row.reference !== previousReference) {
      parity = parity === 0 ? 1 : 0;
    }
    previousReference = row.reference;
    return parity;
  });
}

/**
 * Guards the §3.3 click-to-annotate affordance off until annotation-mode resolves v2 schema
 * ids (see ledger §5). Flip to true once that lands.
 */
export const ANNOTATION_CELL_LINKS_ENABLED = false;

/**
 * Builds the annotation-mode deep link for a cell's reference, percent-encoding both the
 * schema id (path segment) and the reference (query value) so slashes, `&`, `#`, and other
 * reserved characters can't reshape the URL.
 */
export function buildAnnotationUrl(schemaId: string, reference: string): string {
  return `/dataset/${encodeURIComponent(schemaId)}/annotation-mode?_search=${encodeURIComponent(reference)}`;
}
