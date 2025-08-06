import { useResolve } from "ts-injecty";

import { Question } from "@/v1/domain/entities/question/Question";
import { GetLLMExtractionUseCase } from "@/v1/domain/usecases/get-extraction-completion-use-case";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";
import { Data, ReferenceValues, TableData } from "@/v1/domain/entities/table/TableData";


export const useLLMExtractionViewModel = (
  props: { 
    tableJSON: TableData, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }
) => {
    const getExtraction = useResolve(GetLLMExtractionUseCase);
    const { state: dataset } = useDataset();
    const { state: document } = useDocument();

  const completeExtraction = async (
    selectedRowData: Data,
    columns: Array<string>, 
    referenceValues: ReferenceValues,
    headersQuestionName: string = 'context-relevant',
    typesQuestionName: string = 'extraction-source',
    promptQuestionName: string = 'notes',
  ): Promise<Data> => {
    const reference = props.tableJSON.reference || document.reference;
    const schemaName = props.tableJSON.schema?.schemaName || props.tableJSON.validation?.name;
    const headers = getSelectionQuestionAnswer(headersQuestionName)?.filter((value) => value != 'Not listed');
    const types = getSelectionQuestionAnswer(typesQuestionName);
    const prompt = getTextQuestionAnswer(promptQuestionName);

    const predictedData = await getExtraction.getExtractionCompletion(
      reference, 
      schemaName, 
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
      ?.filter((q: Question) => q.name === question_name && typeof q.answer.valuesAnswered === 'string')
      .map((q: Question) => q.answer.valuesAnswered)
      .shift();

    return questionAnswer;
  };

  return {
    completeExtraction,
    document,
  }
};