import { type ColumnMeta } from "./ColumnMeta";

export class SchemaVersion {
  constructor(
    public readonly id: string,
    public readonly schemaId: string,
    public readonly version: number,
    public readonly columnsCache: ColumnMeta[],
    public readonly reviewWidgets: Record<string, Record<string, unknown>>,
    public readonly insertedAt: string
  ) {}

  findColumn(name: string): ColumnMeta | undefined {
    return this.columnsCache.find((column) => column.name === name);
  }
}
