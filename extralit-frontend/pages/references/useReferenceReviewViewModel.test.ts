import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import Container from "ts-injecty";
import { useResolveMock } from "~/v1/di/__mocks__/useResolveMock";
import { GetReferenceReviewUseCase } from "~/v2/domain/usecases/get-reference-review-use-case";
import { SubmitReferenceReviewUseCase, ReviewSubmitError } from "~/v2/domain/usecases/submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "~/v2/domain/usecases/save-review-draft-use-case";
import { DiscardReviewUseCase } from "~/v2/domain/usecases/discard-review-use-case";
import { ReferenceReview } from "~/v2/domain/entities/review/ReferenceReview";
import { useReferenceReviewViewModel } from "./useReferenceReviewViewModel";

vi.mock("~/v1/infrastructure/services/useNotifications", () => ({
  useNotifications: () => ({ notify: vi.fn() }),
}));
vi.mock("~/v1/infrastructure/services/useTranslate", () => ({
  useTranslate: () => ({ t: (key: string) => key, tc: (key: string) => key }),
}));

const REVIEW = new ReferenceReview("10.1000/j.x", [], 0);

describe("useReferenceReviewViewModel", () => {
  beforeEach(() => {
    // Reset the global ts-injecty container so each test's useResolveMock wins.
    Container.dispose();
    setActivePinia(createPinia());
  });

  it("loads the review on mount-equivalent call and exposes it", async () => {
    const execute = vi.fn(async () => REVIEW);
    useResolveMock(GetReferenceReviewUseCase, { execute });
    useResolveMock(SubmitReferenceReviewUseCase, { execute: vi.fn() });
    useResolveMock(SaveReviewDraftUseCase, { execute: vi.fn() });
    useResolveMock(DiscardReviewUseCase, { execute: vi.fn() });

    const vm = useReferenceReviewViewModel("10.1000/j.x", "w-1");
    await vm.load();

    expect(execute).toHaveBeenCalledWith("10.1000/j.x", "w-1");
    // review is held in a ref, so Vue reactive-wraps it (desirable — the form iterates
    // records reactively); assert deep equality rather than raw object identity.
    expect(vm.review.value).toEqual(REVIEW);
  });

  it("collects normalized 422 messages per record on submit failure, then clears on success", async () => {
    useResolveMock(GetReferenceReviewUseCase, { execute: vi.fn(async () => REVIEW) });
    const submit = vi
      .fn()
      .mockRejectedValueOnce(new ReviewSubmitError(["missing value for required question: size"], 422))
      .mockResolvedValueOnce({ id: "resp" });
    useResolveMock(SubmitReferenceReviewUseCase, { execute: submit });
    useResolveMock(SaveReviewDraftUseCase, { execute: vi.fn() });
    useResolveMock(DiscardReviewUseCase, { execute: vi.fn() });

    const vm = useReferenceReviewViewModel("10.1000/j.x", "w-1");
    await vm.onSubmit("r-1", {});
    expect(vm.submitErrors.value["r-1"]).toEqual(["missing value for required question: size"]);

    await vm.onSubmit("r-1", { size: "12" });
    expect(vm.submitErrors.value["r-1"]).toBeUndefined();
  });

  it("reloads the review after a successful submit so the projection flips to response", async () => {
    const load = vi.fn(async () => REVIEW);
    useResolveMock(GetReferenceReviewUseCase, { execute: load });
    useResolveMock(SubmitReferenceReviewUseCase, { execute: vi.fn(async () => ({ id: "resp" })) });
    useResolveMock(SaveReviewDraftUseCase, { execute: vi.fn() });
    useResolveMock(DiscardReviewUseCase, { execute: vi.fn() });

    const vm = useReferenceReviewViewModel("10.1000/j.x", "w-1");
    await vm.load();
    await vm.onSubmit("r-1", { size: "12" });

    expect(load).toHaveBeenCalledTimes(2);
  });
});
