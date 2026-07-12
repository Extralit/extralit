import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";
import { ReviewSubmitError } from "./submit-reference-review-use-case";

export class SaveReviewDraftUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string, values: Record<string, unknown>): Promise<RecordResponse> {
    try {
      return await this.annotationRepository.upsertResponse(recordId, values, "draft");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
