// The out-of-band per-column overlay (parent spec §13). Free-form JSONB: `type` is the
// only key the UI interprets; unknown types fall back to the dtype default.
export interface ReviewOverlay {
  type?: string;
  [key: string]: unknown;
}

// Built from a v1 column `Field` (settings.type === "column") — the column manifest for a
// dataset's current schema version now lives in `Field` rows rather than a
// `SchemaVersion.columns_cache` blob (folded back into `Field.settings` in the v2->v1 fold).
export class ColumnMeta {
  constructor(
    public readonly name: string,
    public readonly dtype: string,
    public readonly nullable: boolean,
    public readonly review: ReviewOverlay | null
  ) {}
}
