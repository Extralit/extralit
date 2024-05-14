import { ref } from "vue-demi";
import { useResolve } from "ts-injecty";

import { Record as FeedbackRecord } from '~/v1/domain/entities/record/Record';
import { Question } from "@/v1/domain/entities/question/Question";
import { Records } from "@/v1/domain/entities/record/Records";
import { useRecords } from "@/v1/infrastructure/storage/RecordsStorage";
import { GetLLMExtractionUseCase } from "@/v1/domain/usecases/get-llm-extraction-use-case";

import { DataFrame, Data, ReferenceValues } from "./types";
import { RecordDataFramesArray } from './tableUtils';
import { columnUniqueCounts } from './dataUtils';
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";


export const useExtractionTableViewModel = (
  props: { 
    tableData: string, 
    editable: boolean, 
    hasValidValues: boolean,
    questions: Question[],
  }, 
) => {
  const tableJSON = ref<DataFrame>(JSON.parse(props.tableData));
  const getExtraction = useResolve(GetLLMExtractionUseCase);
  const { state: records }: { state: Records } = useRecords();
  const { state: dataset } = useDataset();

  const getSelectionQuestionAnswers = (): Record<string, Array<string>> => {
    let questionAnswers = props.questions
      ?.filter(q => Array.isArray(q.answer.valuesAnswered))
      .reduce((acc, q) => {
        acc[q.name] = q.answer.valuesAnswered;
        return acc;
      }, {});

    return questionAnswers;
  };

  const completeExtraction = async (
    selectedRowData: Data,
    columns: Array<string>, 
    referenceValues: ReferenceValues,
    headers_question_name: string = 'context-relevant',
    types_question_name: string = 'extraction-source',
  ): Promise<Data> => {
    const selectionQuestionAnswers = getSelectionQuestionAnswers();
    const headers = selectionQuestionAnswers[headers_question_name].filter((value) => value != 'Not listed');
    const types = selectionQuestionAnswers[types_question_name].filter((value) => value.toLowerCase());
    const reference = tableJSON.value.reference;
    const schema_name = tableJSON.value.validation?.name;

    try {
      const predictedData = await getExtraction.completion(
        reference, 
        schema_name, 
        selectedRowData, 
        referenceValues, 
        columns, 
        headers, 
        types, 
        dataset.workspaceName
      );

      return predictedData.data;
    } catch (error) {
      console.log('error', error);
      return [];
    }
  };

  const getTableDataFromRecords = (filter_fn: (record: FeedbackRecord) => boolean): RecordDataFramesArray => {
    // filter_fn is a function that takes a record and returns true if it should be included in the table
    // returns an array of objects of the form {field: {refValue: {column: value, ...}, ...}, ...}
    let recordTables: RecordDataFramesArray = records.records?.filter(filter_fn)
      .map((rec) => {
        let answer_tables = rec?.answer?.value || {};
        if (answer_tables) {
          answer_tables = Object.fromEntries(
            Object.entries(answer_tables)
              .filter(([key, obj]) => {
                const value = (obj as { value: string; }).value;
                return (typeof value === 'string') && (value.startsWith('{'));
              })
              .map(([key, obj]) => {
                try {
                  const value = (obj as { value: string; }).value;
                  const table = JSON.parse(value);
                  delete table.validation.columns;
                  return [key, table];
                } catch (e) {
                  console.error(e);
                  return [key, {}];
                }
              })
              .filter(([key, obj]) => Object.keys(obj).length > 0)
          );
        }

        let field_table = rec.fields
          .filter((field) => field?.settings?.use_table && field?.content.startsWith('{'))
          .reduce((acc, field) => {
            try {
              acc[field.name] = JSON.parse(field.content);
              delete acc[field.name].validation.columns;
            } finally {
              return acc;
            }
          }, {});

        // ensures that answer tables are prioritized over field tables
        let tables = Object.keys(answer_tables).length ? answer_tables : field_table;
        return tables;
      }).filter((obj) => Object.keys(obj).length > 0);

    return recordTables;
  };

  const findMatchingRefValues = (
    refColumns: string[], 
    records: RecordDataFramesArray,
    filterByColumnUniqueCounts: boolean = false,
  ): Record<string, Record<string, Record<string, any>>> => {
    // refValues is an object of the form {field: refValue}
    // records is an array of objects of the form {table_name: {data: [{reference: refValue, ...}, ...]}}
    // returns an object of the form {field: {refValue: {column: value, ...}, ...}, ...}
    const matchingRefValues: Record<string, Record<string, any>> = {};

    if (!records) return matchingRefValues;

    for (const field of refColumns) {
      for (const recordTables of records) {
        if (!recordTables) continue;
        const matchingTable = Object.values(recordTables)
          .find((table) => table?.validation?.name.toLowerCase() === field.replace(/_ref$/, ''));

        if (!matchingTable) continue;

        if (!matchingTable.hasOwnProperty('columnUniqueCounts')) {
          matchingTable.columnUniqueCounts = columnUniqueCounts(matchingTable)
        }

        const refRows = matchingTable.data.reduce((acc, row) => {
          const filteredRowValues: Record<string, any> = Object.entries(row)
            .filter(([key, value]) => 
              key != "reference" &&
              (!filterByColumnUniqueCounts || 
                matchingTable.data.length <= 1 || 
                !matchingTable?.columnUniqueCounts?.hasOwnProperty(key) || 
                matchingTable.columnUniqueCounts[key] > 1))
            .reduce((obj, [key, value]) => {
              obj[key] = value;
              return obj;
            }, {});
          acc[row.reference] = filteredRowValues;
          return acc;
        }, {});
        matchingRefValues[field] = refRows;
        break; // only need to find the first matching table, since the recordTables is already sorted that the first table is the corrected version
        }
    }

    return matchingRefValues;
  };

  return {
    tableJSON,
    getSelectionQuestionAnswers,
    getTableDataFromRecords,
    findMatchingRefValues,
    completeExtraction,
  }
}