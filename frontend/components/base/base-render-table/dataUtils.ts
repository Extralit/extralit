
import { Data, DataFrame, PanderaSchema, ReferenceValues, Validator, Validators } from './types';


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

export function generateCombinations(referenceValues: ReferenceValues): Data {
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