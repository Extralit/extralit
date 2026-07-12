import { describe, expect, it } from "vitest";
import { normalizeV2ApiError } from "./apiErrors";

const axiosError = (status: number, data: unknown) => ({ isAxiosError: true, response: { status, data } });

describe("normalizeV2ApiError (two 422 body shapes, spec §7)", () => {
  it("handles the domain-error string shape", () => {
    const normalized = normalizeV2ApiError(axiosError(422, { detail: "missing value for required question: size" }));
    expect(normalized).toEqual({ status: 422, messages: ["missing value for required question: size"] });
  });

  it("handles the pydantic array shape", () => {
    const normalized = normalizeV2ApiError(
      axiosError(422, { detail: [{ loc: ["body", "values"], msg: "field required", type: "missing" }] })
    );
    expect(normalized).toEqual({ status: 422, messages: ["body.values: field required"] });
  });

  it("falls back for non-axios errors", () => {
    expect(normalizeV2ApiError(new Error("boom"))).toEqual({ status: null, messages: ["boom"] });
  });
});
