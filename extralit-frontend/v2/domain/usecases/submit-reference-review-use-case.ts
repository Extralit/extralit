import { AnnotationRepository, type RecordResponse } from "~/v2/infrastructure/repositories/AnnotationRepository";
import { normalizeV2ApiError } from "~/v2/infrastructure/repositories/apiErrors";

export class ReviewSubmitError extends Error {
  constructor(
    public readonly messages: string[],
    public readonly status: number | null
  ) {
    super(messages.join("; "));
    this.name = "ReviewSubmitError";
  }
}

export class SubmitReferenceReviewUseCase {
  constructor(private readonly annotationRepository: AnnotationRepository) {}

  async execute(recordId: string, values: Record<string, unknown>): Promise<RecordResponse> {
    try {
      return await this.annotationRepository.upsertResponse(recordId, values, "submitted");
    } catch (error) {
      const { messages, status } = normalizeV2ApiError(error);
      throw new ReviewSubmitError(messages, status);
    }
  }
}
