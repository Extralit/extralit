import { type V2Record } from "./V2Record";

export class RecordsPage {
  constructor(
    public readonly items: V2Record[],
    // Authoritative: v1's Elasticsearch-backed list/search endpoints return an exact count.
    public readonly total: number
  ) {}
}
