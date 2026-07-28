import { type SchemaRecord } from "./SchemaRecord";

export class RecordsPage {
  constructor(
    public readonly items: SchemaRecord[],
    // Authoritative: v1's Elasticsearch-backed list/search endpoints return an exact count.
    public readonly total: number
  ) {}
}
