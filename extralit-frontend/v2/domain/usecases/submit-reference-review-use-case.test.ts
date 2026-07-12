import { describe, expect, it, vi } from "vitest";
import { ReviewSubmitError, SubmitReferenceReviewUseCase } from "./submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "./save-review-draft-use-case";
import { DiscardReviewUseCase } from "./discard-review-use-case";

describe("review response use-cases", () => {
  it("submits with status=submitted", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "submitted" }));
    await new SubmitReferenceReviewUseCase({ upsertResponse } as never).execute("r-1", { size: 12 });

    expect(upsertResponse).toHaveBeenCalledWith("r-1", { size: 12 }, "submitted");
  });

  it("normalizes both 422 shapes into ReviewSubmitError", async () => {
    const upsertResponse = vi.fn(async () => {
      throw { isAxiosError: true, response: { status: 422, data: { detail: "missing value for required question" } } };
    });

    const attempt = new SubmitReferenceReviewUseCase({ upsertResponse } as never).execute("r-1", {});

    await expect(attempt).rejects.toBeInstanceOf(ReviewSubmitError);
    await expect(attempt).rejects.toMatchObject({ messages: ["missing value for required question"], status: 422 });
  });

  it("saves drafts with status=draft", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "draft" }));
    await new SaveReviewDraftUseCase({ upsertResponse } as never).execute("r-1", { size: 12 });

    expect(upsertResponse).toHaveBeenCalledWith("r-1", { size: 12 }, "draft");
  });

  it("discards with null values", async () => {
    const upsertResponse = vi.fn(async () => ({ id: "resp", status: "discarded" }));
    await new DiscardReviewUseCase({ upsertResponse } as never).execute("r-1");

    expect(upsertResponse).toHaveBeenCalledWith("r-1", null, "discarded");
  });
});
