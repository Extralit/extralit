export type SchemaRecordStatus = "pending" | "completed" | "discarded";

export class SchemaRecord {
  constructor(
    public readonly id: string,
    public readonly datasetId: string,
    public readonly reference: string | null,
    public readonly externalId: string | null,
    public readonly fields: Record<string, unknown>,
    public readonly metadata: Record<string, unknown> | null,
    public readonly status: SchemaRecordStatus,
    // Naive ISO strings from the server — treat as UTC (spec §7 gotchas).
    public readonly insertedAt: string,
    public readonly updatedAt: string
  ) {}
}
