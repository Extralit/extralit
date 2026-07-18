import { describe, expect, it, vi } from "vitest";
import type { AxiosInstance } from "axios";
import { AnnotationRepository } from "./AnnotationRepository";

describe("AnnotationRepository", () => {
  it("returns null when GET responses returns literal null with 200 (never 404)", async () => {
    const axios = { get: vi.fn(async () => ({ data: null })) } as unknown as AxiosInstance;

    await expect(new AnnotationRepository(axios).getResponse("r-1")).resolves.toBeNull();
    expect(axios.get).toHaveBeenCalledWith("/v2/records/r-1/responses");
  });

  it("unwraps response values on read", async () => {
    const axios = {
      get: vi.fn(async () => ({
        data: { id: "resp-1", record_id: "r-1", user_id: "u-1", values: { size: { value: 12 } }, status: "draft" },
      })),
    } as unknown as AxiosInstance;

    const response = await new AnnotationRepository(axios).getResponse("r-1");

    expect(response?.values).toEqual({ size: 12 });
    expect(response?.status).toBe("draft");
  });

  it("re-wraps values on upsert PUT", async () => {
    const put = vi.fn(async () => ({
      data: { id: "resp-1", record_id: "r-1", user_id: "u-1", values: { size: { value: 12 } }, status: "submitted" },
    }));
    const axios = { put } as unknown as AxiosInstance;

    await new AnnotationRepository(axios).upsertResponse("r-1", { size: 12 }, "submitted");

    expect(put).toHaveBeenCalledWith("/v2/records/r-1/responses", {
      values: { size: { value: 12 } },
      status: "submitted",
    });
  });

  it("sends null values on the discard path instead of wrapping", async () => {
    const put = vi.fn(async () => ({
      data: { id: "resp-1", record_id: "r-1", user_id: "u-1", values: null, status: "discarded" },
    }));
    const axios = { put } as unknown as AxiosInstance;

    const response = await new AnnotationRepository(axios).upsertResponse("r-1", null, "discarded");

    expect(put).toHaveBeenCalledWith("/v2/records/r-1/responses", { values: null, status: "discarded" });
    expect(response.values).toEqual({});
    expect(response.status).toBe("discarded");
  });

  it("maps suggestions keeping question_id keying and provenance", async () => {
    const axios = {
      get: vi.fn(async () => ({
        data: {
          items: [
            { id: "sug-1", record_id: "r-1", question_id: "q-1", value: 3, score: 0.9, agent: "gpt", type: null },
          ],
        },
      })),
    } as unknown as AxiosInstance;

    const suggestions = await new AnnotationRepository(axios).getSuggestions("r-1");

    expect(suggestions[0]).toMatchObject({ questionId: "q-1", value: 3, score: 0.9, agent: "gpt" });
  });
});
