import { Record as FeedbackRecord } from '@/v1/domain/entities/record/Record';
import { Question } from "@/v1/domain/entities/question/Question";
import { Records } from "@/v1/domain/entities/record/Records";
import { useRecords } from "@/v1/infrastructure/storage/RecordsStorage";

import { columnUniqueCounts } from './dataUtils';

import { TableData } from '~/v1/domain/entities/table/TableData';

type RecordDataFrames = Record<string, TableData>;

export const useReferenceTablesViewModel = (
  props: { 
    tableJSON: TableData,
    editable: boolean, 
  }
) => {
  const { state: records }: { state: Records } = useRecords();

  const getTableDataFromRecords = (filter_fn: (record: FeedbackRecord) => boolean): RecordDataFrames[] => {
    // filter_fn is a function that takes a record and returns true if it should be included in the table
    // returns an array of objects of the form {field: {refValue: {column: value, ...}, ...}, ...}
    let recordTables: RecordDataFrames[] = records.records?.filter(filter_fn)
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
    records: RecordDataFrames[],
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
          .find((table: TableData) => {
            const schemaName = table?.schema?.schemaName || table?.validation?.name;
            return schemaName?.toLowerCase() === field.replace(/(_ref|_ID)$/, '').toLowerCase();
          });

        if (!matchingTable) continue;

        if (!matchingTable.hasOwnProperty('columnUniqueCounts')) {
          matchingTable.columnUniqueCounts = columnUniqueCounts(matchingTable)
        }

        const refRows = matchingTable.data.reduce((acc, row) => {
          const filteredRowValues: Record<string, any> = Object.entries(row)
            .filter(([key, value]) => 
              key != "reference" && key != "_id" &&
              (!filterByColumnUniqueCounts || 
                matchingTable.data.length <= 1 || 
                !matchingTable?.columnUniqueCounts?.hasOwnProperty(key) || 
                matchingTable.columnUniqueCounts[key] > 1))
            .reduce((acc, [key, value]) => {
              acc[key] = value;
              return acc;
            }, {});
          console.log(field, row.reference || row[field])
          acc[row.reference || row[field]] = filteredRowValues;
          return acc;
        }, {});
        matchingRefValues[field] = refRows;
        break; // only need to find the first matching table, since the recordTables is already sorted that the first table is the corrected version
        }
    }

    return matchingRefValues;
  };

  return {
    getTableDataFromRecords,
    findMatchingRefValues,
  }
};
