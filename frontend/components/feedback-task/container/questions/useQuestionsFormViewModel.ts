import { useResolve } from "ts-injecty";
import { ref } from "vue-demi";
import { Record } from "~/v1/domain/entities/record/Record";
import { ClearRecordUseCase } from "~/v1/domain/usecases/clear-record-use-case";
import { DiscardRecordUseCase } from "~/v1/domain/usecases/discard-record-use-case";
import { SubmitRecordUseCase } from "~/v1/domain/usecases/submit-record-use-case";
import { SaveDraftRecord } from "~/v1/domain/usecases/save-draft-use-case";
import { useDebounce } from "~/v1/infrastructure/services/useDebounce";
import { useQueue } from "~/v1/infrastructure/services/useQueue";
import { useBeforeUnload } from "~/v1/infrastructure/services/useBeforeUnload";

export const useQuestionFormViewModel = () => {
  const beforeUnload = useBeforeUnload();
  const queue = useQueue();
  const debounceForSubmit = useDebounce(300);
  const debounceForAutoSave = useDebounce(2000);
  const debounceForSavingMessage = useDebounce(1000);

  const isDraftSaving = ref(false);
  const isDiscarding = ref(false);
  const isSubmitting = ref(false);
  const discardUseCase = useResolve(DiscardRecordUseCase);
  const submitUseCase = useResolve(SubmitRecordUseCase);
  const clearUseCase = useResolve(ClearRecordUseCase);
  const saveDraftUseCase = useResolve(SaveDraftRecord);

  const discard = async (record: Record) => {
    isDiscarding.value = true;
    debounceForAutoSave.stop();
    beforeUnload.destroy();

    await queue.enqueue(() => {
      return discardUseCase.execute(record);
    });

    await debounceForSubmit.wait();

    isDiscarding.value = false;
  };

  const incrementDuration = (record: Record, durationWrapper: { value: number }) => {
    if (!record.hasAnyQuestionAnswered || !record.answer) return;
    if (record.answer.duration === undefined) {
      record.answer.duration = 0;
    }

    record.answer.duration += durationWrapper.value;
    durationWrapper.value = 0; // reset duration for upstream caller to indicate it's been consumed
  }

  const submit = async (record: Record, durationWrapper?: any) => {
    isSubmitting.value = true;
    debounceForAutoSave.stop();
    beforeUnload.destroy();

    if (durationWrapper) {
      incrementDuration(record, durationWrapper);
    }

    await queue.enqueue(() => {
      return submitUseCase.execute(record);
    });

    await debounceForSubmit.wait();

    isSubmitting.value = false;
  };

  const clear = (record: Record) => {
    debounceForAutoSave.stop();
    beforeUnload.destroy();

    queue.enqueue(() => {
      return clearUseCase.execute(record);
    });
  };

  const onSaveDraft = async (record: Record) => {
    if (!record.hasAnyQuestionAnswered) return;
    isDraftSaving.value = true;

    try {
      beforeUnload.confirm();
      await saveDraftUseCase.execute(record);
    } finally {
      await debounceForSavingMessage.wait();

      isDraftSaving.value = false;
      beforeUnload.destroy();
    }
  };

  const saveDraft = async (record: Record, durationWrapper?: any) => {
    if (record.isSubmitted) return;
    beforeUnload.confirm();
    await debounceForAutoSave.wait();

    if (durationWrapper) {
      incrementDuration(record, durationWrapper);
    }

    queue.enqueue(() => {
      return onSaveDraft(record);
    });
  };

  const saveDraftImmediately = (record: Record, durationWrapper?: any) => {
    if (record.isSubmitted) return;
    debounceForAutoSave.stop();

    if (durationWrapper) {
      incrementDuration(record, durationWrapper);
    }

    queue.enqueue(() => {
      return onSaveDraft(record);
    });
  };

  return {
    draftSaving: isDraftSaving,
    isDiscarding,
    isSubmitting,
    clear,
    submit,
    discard,
    saveDraft,
    saveDraftImmediately,
  };
};
