import { useStoreFor } from "@/v1/store/create";
import { ReferenceReview } from "~/v2/domain/entities/review/ReferenceReview";

// Keyed by reference, not by route, so Phase 5's Queue UI can drive the same store
// with references from GET /queues/{id}/next (spec §7).
class ReferenceReviews {
  constructor(public readonly byReference: Record<string, ReferenceReview> = {}) {}
}

interface IReferenceReviewsStorage {
  saveReview(review: ReferenceReview): void;
  findByReference(reference: string): ReferenceReview | undefined;
}

const useStoreForReferenceReviews = useStoreFor<ReferenceReviews, IReferenceReviewsStorage>(ReferenceReviews);

export const useReferenceReviews = () => {
  const store = useStoreForReferenceReviews();

  const saveReview = (review: ReferenceReview) => {
    store.save(new ReferenceReviews({ ...store.get().byReference, [review.reference]: review }));
  };

  const findByReference = (reference: string): ReferenceReview | undefined => store.get().byReference[reference];

  return { ...store, saveReview, findByReference };
};
