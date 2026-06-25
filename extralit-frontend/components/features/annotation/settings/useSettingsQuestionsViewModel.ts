import { ref } from "vue";
import { useResolve } from "ts-injecty";
import { Question } from "~/v1/domain/entities/question/Question";
import { UpdateQuestionSettingUseCase } from "~/v1/domain/usecases/dataset-setting/update-question-setting-use-case";

export const useSettingsQuestionsViewModel = () => {
  const updateQuestionSettingsUseCase = useResolve(UpdateQuestionSettingUseCase);
  const newLabelText = ref({});

  const restore = (question: Question) => {
    question.restore();
  };

  const update = async (question: Question) => {
    try {
      await updateQuestionSettingsUseCase.execute(question);
    } catch (error) {
      // TODO
    }
  };

  const addOption = (question: Question) => {
    const text = newLabelText.value[question.id]?.trim();
    if (!text) return;

    const existingOption = question.settings.options.find(option =>
      option.value.toLowerCase() === text.toLowerCase() ||
      option.text.toLowerCase() === text.toLowerCase()
    );

    if (existingOption) {
      // TODO: Show error message that option already exists
      return;
    }

    question.settings.options.push({
      value: text.toLowerCase().replace(/\s+/g, '_'),
      text
    });

    newLabelText.value[question.id] = '';

    question.reloadAnswerFromOptions();
  };

  const deleteOption = (question: Question, optionToDelete: any) => {
    const index = question.settings.options.findIndex(option =>
      option.value === optionToDelete.value
    );

    if (index > -1) {
      question.settings.options.splice(index, 1);
      question.reloadAnswerFromOptions();
    }
  };

  return {
    restore,
    update,
    newLabelText,
    addOption,
    deleteOption,
  };
};
