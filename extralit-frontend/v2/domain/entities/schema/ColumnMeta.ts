// The out-of-band per-column overlay (parent spec §13). Free-form JSONB: `type` is the
// only key the UI interprets; unknown types fall back to the dtype default.
export interface ReviewOverlay {
  type?: string;
  [key: string]: unknown;
}

export class ColumnMeta {
  constructor(
    public readonly name: string,
    public readonly dtype: string,
    public readonly nullable: boolean,
    public readonly review: ReviewOverlay | null
  ) {}
}
