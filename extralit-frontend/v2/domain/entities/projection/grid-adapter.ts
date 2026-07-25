import { type WorkspaceProjection } from "./WorkspaceProjection";

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
      record[column.name] = cell ? toScalarCell(cell.value) : null;
    }
    return record;
  });
}

/**
 * Coerces a cell value to something Perspective can build a column schema from.
 *
 * Perspective infers each column's type from the (assumed-scalar) shape of its cell
 * values — it has no notion of an array- or object-typed column. The backend's
 * `QuestionType` enum, though, includes `multi_label_selection` (array of labels),
 * `ranking` (array of ranked items), and `span` (an object) — all non-scalar. Feeding one
 * of those straight into `client.table()` either renders as `[object Object]` or makes the
 * whole `table()` call reject (see grid-adapter.test.ts / ExtractionsGrid's `performLoad`
 * doc comment for what happens to that rejection). Serializing arrays/objects to a stable
 * JSON string keeps every column scalar. `null` is passed through as-is (not the string
 * `"null"`) because the manifest-completeness contract in `toPerspectiveData`'s doc comment
 * depends on an absent/empty cell being `null`. Genuine scalars (string/number/boolean) are
 * passed through unchanged.
 *
 * `JSON.stringify` itself does not unconditionally return a string: it returns `undefined`
 * (not a string) for a function or a symbol, and throws for a `BigInt` or a circular
 * structure. Server JSON can't produce any of those today, but this helper is the one place
 * that is supposed to make the "every column present, `null` when absent" contract
 * unconditional — so both failure modes are coerced to `null` rather than left to leak
 * `undefined` into a "present" key or throw and escape as a spurious `load-error` out of
 * `performLoad`.
 */
function toScalarCell(value: unknown): unknown {
  if (value === null || value === undefined) {
    return null;
  }
  const valueType = typeof value;
  if (valueType === "string" || valueType === "number" || valueType === "boolean") {
    return value;
  }
  try {
    return JSON.stringify(value) ?? null;
  } catch {
    return null;
  }
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
