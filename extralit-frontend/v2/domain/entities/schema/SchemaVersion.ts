export class SchemaVersion {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly version: number,
    public readonly insertedAt: string
  ) {}
}
