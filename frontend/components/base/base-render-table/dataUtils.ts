
import { Record as FeedbackRecord } from '~/v1/domain/entities/record/Record';
import { RecordDataFramesArray } from './tableUtils';
import { DataFrame, PanderaSchema, Validator, Validators } from './types';
import { Tabulator, RangeComponent, RowComponent } from "tabulator-tables";


export function columnUniqueCounts(tableJSON: DataFrame): Record<string, number> {
  // tableJSON is an object of the form {data: [{column: value, ...}, ...]}
  // returns an object of the form {column: uniqueCount, ...}
  let uniqueCounts: Record<string, number> = {};
  for (let key of Object.keys(tableJSON.data[0])) {
    let values = tableJSON.data
      .map(row => row[key])
      .filter(value => value != null && value !== 'NA');
    uniqueCounts[key] = new Set(values).size;
  }

  return uniqueCounts;
}

export function findMatchingRefValues(refColumns: string[], records: RecordDataFramesArray): Record<string, Record<string, Record<string, any>>> {
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





export function getMaxStringValue(columnName: string, data: any[]): string {
  return data.reduce((max, row) => row[columnName] > max ? row[columnName] : max, "");
}

export function incrementReferenceStr(reference: string): string {
  if (!reference) return undefined;
  const prefix = reference.slice(0, 1);

  const numericalPart = reference.slice(1);
  if (!/^\d+$/.test(numericalPart)) return undefined; 

  const incrementedDigits = String(parseInt(numericalPart) + 1).padStart(numericalPart.length, '0');
  const newReference = `${prefix}${incrementedDigits}`;

  return newReference;
}

export function generateCombinations(referenceValues: Record<string, Record<string, any>>): Record<string, string>[] {
  const referenceKeys: Record<string, string[]> = Object.keys(referenceValues).reduce((acc, key) => {
    acc[key] = Object.keys(referenceValues[key]);
    return acc;
  }, {});

  const refKeys = Object.keys(referenceKeys);
  const refValueCombinations = cartesianProduct(refKeys.map(key => referenceKeys[key]));

  const refCombinations = refValueCombinations.map(refValues => {
    return refValues.reduce((acc, value, index) => {
      acc[refKeys[index]] = value;
      return acc;
    }, {} as Record<string, string>);
  });

  return refCombinations;
}

function cartesianProduct(arr: any[][]): any[][] {
  return arr.reduce((a, b) => a.flatMap((x: any[]) => b.map((y: any) => [...x, y])), [[]]);
}