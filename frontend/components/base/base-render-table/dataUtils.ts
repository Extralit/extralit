import { useRecordFeedbackTaskViewModel } from '@/components/feedback-task/container/useRecordFeedbackTaskViewModel';
import { Record as FeedbackRecord } from '~/v1/domain/entities/record/Record';
import { RecordDataFramesArray } from './tableUtils';
import { DataFrame, Validation, ValidationSpec, ValidationSpecs } from './types';

export function columnUniqueCounts(tableJSON: DataFrame): Record<string, number> {
  // tableJSON is an object of the form {data: [{column: value, ...}, ...]}
  // returns an object of the form {column: uniqueCount, ...}
  let uniqueCounts: Record<string, number> = {};
  for (let key of Object.keys(tableJSON.data[0])) {
    let values = tableJSON.data.map(row => row[key]);
    let filteredValues = values.filter(value => value != null && value !== 'NA' && value);
    uniqueCounts[key] = new Set(filteredValues).size;
  }

  return uniqueCounts;
}

export function findMatchingRefValues(refColumns: string[], records: RecordDataFramesArray): Record<string, Record<string, any>> {
  // refValues is an object of the form {field: refValue}
  // records is an array of objects of the form {table_name: {data: [{reference: refValue, ...}, ...]}}
  // returns an object of the form {field: {refValue: {column: value, ...}, ...}, ...}
  const matchingRefValues: Record<string, Record<string, any>> = {};

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
            (matchingTable.data.length <= 1 || !matchingTable?.columnUniqueCounts?.hasOwnProperty(key) || matchingTable.columnUniqueCounts[key] > 1))
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
}


export function getTableDataFromRecords(filter_fn: (record: FeedbackRecord) => boolean): RecordDataFramesArray {
  // filter_fn is a function that takes a record and returns true if it should be included in the table
  // returns an array of objects of the form {field: {refValue: {column: value, ...}, ...}, ...}
  let recordTables: RecordDataFramesArray = useRecordFeedbackTaskViewModel({ recordCriteria: null })?.records.records
    .filter(filter_fn)
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
}


export function getMaxStringValue(columnName: string, data: any[]): string {
  return data.reduce((max, row) => row[columnName] > max ? row[columnName] : max, "");
}

export function incrementReferenceStr(reference: string): string {
  const parts = reference.split("-");
  const lastPart = parts[parts.length - 1];
  const suffix = lastPart.slice(-1);
  const incrementedDigits = String(parseInt(lastPart) + 1).padStart(lastPart.length - suffix.length, '0');
  const newReference = `${parts.slice(0, -1).join("-")}-${incrementedDigits}${suffix}`;

  return newReference;
}