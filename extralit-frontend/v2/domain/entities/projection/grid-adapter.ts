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
 * question order is definition order, not alphabetical, and JS object key order is not a
 * safe substitute once column names could look numeric). `reference` is emitted first so
 * every row shares an identical, stably-ordered key set — every manifest column is present
 * on every row (`null` when the cell is absent) so Perspective infers one stable schema
 * instead of a per-row-varying one.
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
 * Builds the annotation-mode deep link for a cell's reference, percent-encoding the
 * reference so slashes and other reserved characters survive the query string.
 */
export function buildAnnotationUrl(schemaId: string, reference: string): string {
  return `/dataset/${schemaId}/annotation-mode?_search=${encodeURIComponent(reference)}`;
}
