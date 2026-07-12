export type FilterOp = "eq" | "in" | "ge" | "le";

export interface RecordFilter {
  column: string;
  op: FilterOp;
  value: unknown;
}

export class SearchCriteria {
  constructor(
    public readonly text: string | null = null,
    public readonly filters: RecordFilter[] = [],
    public readonly offset: number = 0,
    public readonly limit: number = 50
  ) {}

  toQueryBody() {
    return {
      text: this.text || null,
      // ge/le with null silently matches nothing server-side — drop them here.
      filters: this.filters.filter((f) => !((f.op === "ge" || f.op === "le") && f.value === null)),
      offset: this.offset,
      limit: this.limit,
    };
  }
}
