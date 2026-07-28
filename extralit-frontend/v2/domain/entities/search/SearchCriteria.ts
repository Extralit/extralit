export type FilterOp = "eq" | "in" | "ge" | "le";

export interface RecordFilter {
  column: string;
  op: FilterOp;
  value: unknown;
}

// v1's RecordFilterScope: `property` is restricted server-side to RecordSortField
// (id | external_id | inserted_at | updated_at | status) — see records.py:260-267.
interface BackendRecordFilterScope {
  entity: "record";
  property: string;
}

interface BackendTermsFilter {
  type: "terms";
  scope: BackendRecordFilterScope;
  values: string[];
}

interface BackendRangeFilter {
  type: "range";
  scope: BackendRecordFilterScope;
  ge?: unknown;
  le?: unknown;
}

type BackendFilter = BackendTermsFilter | BackendRangeFilter;

// Translates the domain's flat {column, op, value} filter into v1's SearchRecordsQuery
// filter shape (api/schemas/v1/records.py:296-372): eq/in become a `terms` filter,
// ge/le become a `range` filter, both scoped through a RecordFilterScope.
const toBackendFilter = (filter: RecordFilter): BackendFilter => {
  const scope: BackendRecordFilterScope = { entity: "record", property: filter.column };
  switch (filter.op) {
    case "eq":
      return { type: "terms", scope, values: [String(filter.value)] };
    case "in":
      return { type: "terms", scope, values: (filter.value as unknown[]).map(String) };
    case "ge":
      return { type: "range", scope, ge: filter.value as string | number };
    case "le":
      return { type: "range", scope, le: filter.value as string | number };
  }
};

export class SearchCriteria {
  constructor(
    public readonly text: string | null = null,
    public readonly filters: RecordFilter[] = [],
    public readonly offset: number = 0,
    public readonly limit: number = 50
  ) {}

  // Body for `POST /datasets/{id}/records/search` — offset/limit travel as query params,
  // not in this body (see V2RecordRepository.searchRecords).
  toQueryBody() {
    // ge/le with null silently matches nothing server-side — drop them here.
    const activeFilters = this.filters.filter((f) => !((f.op === "ge" || f.op === "le") && f.value === null));
    return {
      query: this.text ? { text: { q: this.text } } : null,
      filters: activeFilters.length > 0 ? { and: activeFilters.map(toBackendFilter) } : null,
    };
  }
}
