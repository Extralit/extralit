import { useResolve } from "ts-injecty";

import { Question } from "@/v1/domain/entities/question/Question";
import { GetLLMExtractionUseCase } from "@/v1/domain/usecases/get-extraction-completion-use-case";

import { Data, ReferenceValues } from "./types";
import { SchemaTableViewModel } from "./useSchemaTableViewModel";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";

export const useLLMExtractionViewModel = (
  props: { 
    tableData: string, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }, 
  schemaTableViewModel: SchemaTableViewModel) => {
    const getExtraction = useResolve(GetLLMExtractionUseCase);
    const { state: dataset } = useDataset();
    const { state: document } = useDocument();

  const completeExtraction = async (
    selectedRowData: Data,
    columns: Array<string>, 
    referenceValues: ReferenceValues,
    headers_question_name: string = 'context-relevant',
    types_question_name: string = 'extraction-source',
    prompt_question_name: string = 'notes',
  ): Promise<Data> => {
    const reference = schemaTableViewModel.tableJSON.value.reference || document.reference;
    const schema_name = schemaTableViewModel.tableJSON.value.schema?.schemaName || schemaTableViewModel.tableJSON.value.validation?.name;
    const headers = getSelectionQuestionAnswer(headers_question_name)?.filter((value) => value != 'Not listed');
    const types = getSelectionQuestionAnswer(types_question_name);
    const prompt = getTextQuestionAnswer(prompt_question_name);

    const predictedData = await getExtraction.getExtractionCompletion(
      reference, 
      schema_name, 
      dataset.workspaceName,
      selectedRowData, 
      referenceValues,
      columns, 
      headers, 
      types, 
      prompt,
    );

    return predictedData.data;
  };

  const getSelectionQuestionAnswer = (question_name: string): Array<string> | undefined => {
    let questionAnswers = props.questions
      ?.filter(q => q.name === question_name && Array.isArray(q.answer.valuesAnswered))
      .map(q => q.answer.valuesAnswered)
      .shift();

    return questionAnswers;
  };

  const getTextQuestionAnswer = (question_name: string): string | undefined => {
    let questionAnswer = props.questions
      ?.filter(q => q.name === question_name && typeof q.answer.valuesAnswered === 'string')
      .map(q => q.answer.valuesAnswered)
      .shift();

    return questionAnswer;
  };

  return {
    completeExtraction,
    document,
  }
};