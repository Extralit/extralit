import { describe, expect, it } from "vitest";
import { SearchCriteria } from "./SearchCriteria";

describe("SearchCriteria serialization", () => {
  it("serializes text, filters, offset and limit to the RecordSearchQuery body", () => {
    const criteria = new SearchCriteria("malaria", [{ column: "status", op: "eq", value: "pending" }], 20, 10);

    expect(criteria.toQueryBody()).toEqual({
      text: "malaria",
      filters: [{ column: "status", op: "eq", value: "pending" }],
      offset: 20,
      limit: 10,
    });
  });

  it("omits empty text as null and defaults paging", () => {
    expect(new SearchCriteria("").toQueryBody()).toEqual({ text: null, filters: [], offset: 0, limit: 50 });
  });

  it("drops ge/le filters whose value is null (server silently matches nothing, §10.1-D)", () => {
    const criteria = new SearchCriteria(null, [
      { column: "score", op: "ge", value: null },
      { column: "score", op: "le", value: 5 },
    ]);

    expect(criteria.toQueryBody().filters).toEqual([{ column: "score", op: "le", value: 5 }]);
  });
});
