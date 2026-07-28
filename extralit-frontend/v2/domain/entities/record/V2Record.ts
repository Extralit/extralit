export type V2RecordStatus = "pending" | "completed" | "discarded";

export class V2Record {
  constructor(
    public readonly id: string,
    public readonly datasetId: string,
    public readonly reference: string | null,
    public readonly externalId: string | null,
    public readonly fields: Record<string, unknown>,
    public readonly metadata: Record<string, unknown> | null,
    public readonly status: V2RecordStatus,
    // Naive ISO strings from the server — treat as UTC (spec §7 gotchas).
    public readonly insertedAt: string,
    public readonly updatedAt: string
  ) {}
}
