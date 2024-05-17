import { ref, onBeforeMount } from "vue-demi";
import { useResolve } from "ts-injecty";

import { Record as FeedbackRecord } from '~/v1/domain/entities/record/Record';
import { Question } from "@/v1/domain/entities/question/Question";
import { Records } from "@/v1/domain/entities/record/Records";
import { useRecords } from "@/v1/infrastructure/storage/RecordsStorage";
import { GetLLMExtractionUseCase } from "@/v1/domain/usecases/get-extraction-completion-use-case";
import { GetExtractionSchemaUseCase } from "@/v1/domain/usecases/get-extraction-schema-use-case";

import { DataFrame, Data, ReferenceValues, PanderaSchema } from "./types";
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
  const getExtraction = useResolve(GetLLMExtractionUseCase);
  const getSchema = useResolve(GetExtractionSchemaUseCase);
  const { state: records }: { state: Records } = useRecords();
  const { state: dataset } = useDataset();

  const tableJSON = ref<DataFrame>(JSON.parse(props.tableData));
  const validation = ref<PanderaSchema | null>(null);
  const indexColumns = ref(tableJSON.value?.schema?.primaryKey || []);
  const refColumns = ref(
    tableJSON.value?.schema?.fields
      .map(field => field.name)
      .filter(name => typeof name === 'string' && name.endsWith('_ref')) || []
  );
  const groupbyColumns = ref(refColumns.value || null);

  const waitForWorkspaceName = (interval=100) => {
    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        if (dataset.workspaceName) {
          clearInterval(checkInterval);
          resolve(true);
        }
      }, interval);
    });
  };

  const fetchValidation = async ({ latest = false }: { latest?: boolean } = {}) => {
    var schemaName: string = tableJSON.value.schema?.schemaName;
    var version_id: string = latest ? null : tableJSON.value.schema?.version_id;
    await waitForWorkspaceName();
    
    if (!tableJSON.value.schema.schemaName) {
      schemaName = tableJSON.value?.validation?.name;
    }
    const [schema, fileMetadata] = await getSchema.fetch(dataset.workspaceName, schemaName, version_id);

    tableJSON.value.schema = {
      ...tableJSON.value.schema,
      ...fileMetadata
    };
    validation.value = schema;
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

  const completeExtraction = async (
    selectedRowData: Data,
    columns: Array<string>, 
    referenceValues: ReferenceValues,
    headers_question_name: string = 'context-relevant',
    types_question_name: string = 'extraction-source',
    prompt_question_name: string = 'notes',
  ): Promise<Data> => {
    const reference = tableJSON.value.reference;
    const schema_name = tableJSON.value.schema?.schemaName || tableJSON.value.validation?.name;
    const headers = getSelectionQuestionAnswer(headers_question_name).filter((value) => value != 'Not listed');
    const types = getSelectionQuestionAnswer(types_question_name);
    const prompt = getTextQuestionAnswer(prompt_question_name);

    const predictedData = await getExtraction.completion(
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
    filterByColumnUniqueCounts: boolean = true,
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
          .find((table: DataFrame) => {
            const schemaName = table?.schema?.schemaName || table?.validation?.name;
            return schemaName.toLowerCase() === field.replace(/_ref$/, '')
          });

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
    validation,
    indexColumns,
    refColumns,
    groupbyColumns,
    fetchValidation,
    getTableDataFromRecords,
    findMatchingRefValues,
    completeExtraction,
  }
}