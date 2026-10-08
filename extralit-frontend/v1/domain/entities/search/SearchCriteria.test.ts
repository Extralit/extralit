import { describe, expect, it } from "vitest";
import { SearchCriteria } from "./SearchCriteria";

describe("SearchCriteria serialization", () => {
  it("serializes text into v1's Query.text.q shape", () => {
    const criteria = new SearchCriteria("malaria", [], 20, 10);

    expect(criteria.toQueryBody()).toEqual({
      query: { text: { q: "malaria" } },
      filters: null,
    });
    expect(criteria.offset).toBe(20);
    expect(criteria.limit).toBe(10);
  });

  it("omits empty text as a null query and defaults paging", () => {
    const criteria = new SearchCriteria("");

    expect(criteria.toQueryBody()).toEqual({ query: null, filters: null });
    expect(criteria.offset).toBe(0);
    expect(criteria.limit).toBe(50);
  });

  it("translates an eq filter into a terms filter scoped to the record entity", () => {
    const criteria = new SearchCriteria(null, [{ column: "status", op: "eq", value: "pending" }]);

    expect(criteria.toQueryBody().filters).toEqual({
      and: [{ type: "terms", scope: { entity: "record", property: "status" }, values: ["pending"] }],
    });
  });

  it("translates an in filter into a terms filter with every value stringified", () => {
    const criteria = new SearchCriteria(null, [{ column: "status", op: "in", value: ["pending", "completed"] }]);

    expect(criteria.toQueryBody().filters).toEqual({
      and: [{ type: "terms", scope: { entity: "record", property: "status" }, values: ["pending", "completed"] }],
    });
  });

  it("translates ge/le filters into a range filter", () => {
    const criteria = new SearchCriteria(null, [
      { column: "inserted_at", op: "ge", value: "2026-01-01" },
      { column: "inserted_at", op: "le", value: "2026-02-01" },
    ]);

    expect(criteria.toQueryBody().filters).toEqual({
      and: [
        { type: "range", scope: { entity: "record", property: "inserted_at" }, ge: "2026-01-01" },
        { type: "range", scope: { entity: "record", property: "inserted_at" }, le: "2026-02-01" },
      ],
    });
  });

  it("drops ge/le filters whose value is null (server silently matches nothing, §10.1-D)", () => {
    const criteria = new SearchCriteria(null, [
      { column: "score", op: "ge", value: null },
      { column: "score", op: "le", value: 5 },
    ]);

    expect(criteria.toQueryBody().filters).toEqual({
      and: [{ type: "range", scope: { entity: "record", property: "score" }, le: 5 }],
    });
  });

  it("nulls out filters entirely when every filter was dropped", () => {
    const criteria = new SearchCriteria(null, [{ column: "score", op: "ge", value: null }]);

    expect(criteria.toQueryBody().filters).toBeNull();
  });
});
