import { Record as FeedbackRecord } from '@/v1/domain/entities/record/Record';
import { Records } from "@/v1/domain/entities/record/Records";
import { useRecords } from "@/v1/infrastructure/storage/RecordsStorage";

import { Data, ReferenceValues, TableData } from '~/v1/domain/entities/table/TableData';

type RecordDataFrames = Record<string, TableData>;

export const useReferenceTablesViewModel = (
  props: { 
    tableJSON: TableData,
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
          matchingTable.columnUniqueCounts = matchingTable.getColumnUniqueCounts()
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

  const getColumnMaxValue = (
    columnName: string, data: Data
  ): any => {
    return data.reduce((max, row) => !max || row[columnName] > max ? row[columnName] : max, null);
  }

  const incrementReferenceStr = (
    reference: string
  ): string => {
    if (typeof reference !== 'string') return undefined;
    const prefix = reference.slice(0, 1);

    const numericalPart = reference.slice(1);
    if (!/^\d+$/.test(numericalPart)) return undefined;

    const incrementedDigits = String(parseInt(numericalPart) + 1).padStart(numericalPart.length, '0');
    const newReference = `${prefix}${incrementedDigits}`;

    return newReference;
  }

  const generateCombinations = (
    columnValues: ReferenceValues, fixedValues: Record<string, string> = {}
  ): Data => {
    const possibleKeyValues: Record<string, string[]> = Object.keys(columnValues).reduce((acc, key) => {
      if (!fixedValues[key]) {
        acc[key] = Object.keys(columnValues[key]);
      }
      return acc;
    }, {});

    const keys = Object.keys(possibleKeyValues);
    const valueCombinations = cartesianProduct(keys.map(key => possibleKeyValues[key]));

    const keyValueCombinations = valueCombinations.map(values => {
      return values.reduce((acc, value, index) => {
        acc[keys[index]] = value;
        return acc;
      }, { ...fixedValues } as Record<string, string>);
    });

    return keyValueCombinations;
  }

  return {
    getTableDataFromRecords,
    findMatchingRefValues,
    getColumnMaxValue,
    incrementReferenceStr,
    generateCombinations,
  }
};

function cartesianProduct(arr: any[][]): any[][] {
  return arr.reduce((a, b) => a.flatMap((x: any[]) => b.map((y: any) => [...x, y])), [[]]);
}
