import { type V2Record } from "./V2Record";

export class RecordsPage {
  constructor(
    public readonly items: V2Record[],
    // Approximate by contract (§10.1-D): stale Lance ids are skipped on hydration and FTS
    // totals saturate at 10,000 — pagination must not promise exact counts.
    public readonly total: number
  ) {}
}
