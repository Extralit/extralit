import { ref } from "vue";
import { useResolve } from "ts-injecty";
import { GetReferenceReviewUseCase } from "~/v2/domain/usecases/get-reference-review-use-case";
import { SubmitReferenceReviewUseCase, ReviewSubmitError } from "~/v2/domain/usecases/submit-reference-review-use-case";
import { SaveReviewDraftUseCase } from "~/v2/domain/usecases/save-review-draft-use-case";
import { DiscardReviewUseCase } from "~/v2/domain/usecases/discard-review-use-case";
import { ReferenceReview } from "~/v2/domain/entities/review/ReferenceReview";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { useTranslate } from "~/v1/infrastructure/services/useTranslate";

export const useReferenceReviewViewModel = (reference: string, workspaceId: string) => {
  const getReviewUseCase = useResolve(GetReferenceReviewUseCase);
  const submitUseCase = useResolve(SubmitReferenceReviewUseCase);
  const saveDraftUseCase = useResolve(SaveReviewDraftUseCase);
  const discardUseCase = useResolve(DiscardReviewUseCase);
  const notifications = useNotifications();
  const { t } = useTranslate();

  const review = ref<ReferenceReview | null>(null);
  const isLoading = ref(false);
  const loadFailed = ref(false);
  const submitErrors = ref<Record<string, string[]>>({});

  const load = async () => {
    isLoading.value = true;
    loadFailed.value = false;
    try {
      review.value = await getReviewUseCase.execute(reference, workspaceId);
    } catch {
      loadFailed.value = true;
    } finally {
      isLoading.value = false;
    }
  };

  const runAction = async (recordId: string, action: () => Promise<unknown>, successKey: string) => {
    try {
      await action();
      const { [recordId]: _cleared, ...rest } = submitErrors.value;
      submitErrors.value = rest;
      notifications.notify({ message: t(successKey), type: "success" });
      await load(); // re-read: projection source flips response/suggestion server-side
    } catch (error) {
      if (error instanceof ReviewSubmitError) {
        submitErrors.value = { ...submitErrors.value, [recordId]: error.messages };
      } else {
        throw error;
      }
    }
  };

  const onSubmit = (recordId: string, values: Record<string, unknown>) =>
    runAction(recordId, () => submitUseCase.execute(recordId, values), "review.submitted");
  const onSaveDraft = (recordId: string, values: Record<string, unknown>) =>
    runAction(recordId, () => saveDraftUseCase.execute(recordId, values), "review.draftSaved");
  const onDiscard = (recordId: string) =>
    runAction(recordId, () => discardUseCase.execute(recordId), "review.discarded");

  return { review, isLoading, loadFailed, submitErrors, load, onSubmit, onSaveDraft, onDiscard };
};
