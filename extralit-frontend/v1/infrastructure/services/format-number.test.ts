import { describe, it, expect } from "vitest";
import { formatNumber, formatNumberToK } from "./format-number";

describe("format-number", () => {
  it("formats plain numbers with locale grouping", () => {
    expect(formatNumber(1000)).toBe("1,000");
  });

  it("formats large numbers to compact K/M notation", () => {
    expect(formatNumberToK(12000, 2)).toBe("12K");
    expect(formatNumberToK(1500, 1)).toBe("1.5K");
    expect(formatNumberToK(1234567, 2)).toBe("1.23M");
  });

  it("leaves sub-thousand numbers unscaled", () => {
    expect(formatNumberToK(999, 2)).toBe("999");
  });
});
