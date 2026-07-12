import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";
import { ReviewSubmitError } from "./submit-reference-review-use-case";

export class DiscardReviewUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string): Promise<RecordResponse> {
    try {
      // Discarding reverts the projection cell to the suggestion (server filters submitted only).
      return await this.annotationRepository.upsertResponse(recordId, null, "discarded");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
