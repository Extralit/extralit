
import { Data, TableData, ValidationSchema, ReferenceValues, Validator, Validators } from './types';


export function columnUniqueCounts(tableJSON: TableData): Record<string, number> {
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


export function getMaxValue(columnName: string, data: Data): any {
  return data.reduce((max, row) => !max || row[columnName] > max ? row[columnName] : max, null);
}

export function incrementReferenceStr(reference: string): string {
  if (typeof reference !== 'string') return undefined;
  const prefix = reference.slice(0, 1);

  const numericalPart = reference.slice(1);
  if (!/^\d+$/.test(numericalPart)) return undefined; 

  const incrementedDigits = String(parseInt(numericalPart) + 1).padStart(numericalPart.length, '0');
  const newReference = `${prefix}${incrementedDigits}`;

  return newReference;
}

export function generateCombinations(columnValues: ReferenceValues, fixedValues: Record<string, string> = {}): Data {
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
    }, {...fixedValues} as Record<string, string>);
  });

  return keyValueCombinations;
}

function cartesianProduct(arr: any[][]): any[][] {
  return arr.reduce((a, b) => a.flatMap((x: any[]) => b.map((y: any) => [...x, y])), [[]]);
}