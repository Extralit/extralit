import { Question } from "~/v1/domain/entities/question/Question";
import { useDocument } from "~/v1/infrastructure/storage/DocumentStorage";

export const useQuestionsViewModel = ({
  questions,
}: {
  questions: Question[];
}) => {
  const { state: document } = useDocument();

  const suggestion = document.getQuestionSelectionSuggestion();

  questions.forEach((question: Question) => {
    if (suggestion.suggestedAnswer && question.name == 'context-relevant' && 
        ["dynamic_multi_label_selection", "dynamic_label_selection"].includes(question.settings.type)){
      question.addDynamicSelectionToLabelQuestion(suggestion)
      console.log(suggestion, question);
    }
  });
  
  const enableSpanQuestionShortcutsGlobal =
    questions.filter((q) => q.isSpanType).length === 1;

  return { 
    enableSpanQuestionShortcutsGlobal 
  };
};
