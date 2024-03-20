import { useRecordFeedbackTaskViewModel } from '@/components/feedback-task/container/useRecordFeedbackTaskViewModel';
import { Record as FeedbackRecord } from '~/v1/domain/entities/record/Record';
import { DataFrame, Validation, ColumnValidators } from './types';


export function isTableJSON(value: string): boolean {
  if (!value?.length || (!value.startsWith('{') && !value.startsWith('['))) { return false; }
  
  try {
    JSON.parse(value);
    return true;
  } catch (e) {
    console.log(e)
    return false;
  }
}

export function columnUniqueCounts(tableJSON: DataFrame): any {
  // tableJSON is an object of the form {data: [{column: value, ...}, ...]}
  // returns an object of the form {column: uniqueCount, ...}
  let uniqueCounts = {};
  for (let key of Object.keys(tableJSON.data[0])) {
    let values = tableJSON.data.map(row => row[key]);
    let filteredValues = values.filter(value => value != null && value !== 'NA' && value);
    uniqueCounts[key] = new Set(filteredValues).size;
  }

  return uniqueCounts;
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

export function findMatchingRefValues(refValues: Record<string, string>, records: FeedbackRecord[]): any {
  // refValues is an object of the form {field: refValue}
  // records is an array of objects of the form {table_name: {data: [{reference: refValue, ...}, ...]}}
  // returns an object of the form {field: {refValue: {column: value, ...}, ...}, ...}
  const matchingRefValues = {};

  for (const [field, refValue] of Object.entries(refValues)) {
    for (const recordTables of records) {
      if (!recordTables) continue;
      const matchingTable = Object.values(recordTables)
        .find((table) => 
          (!table?.validation?.name || table?.validation?.name.toLowerCase() === field.split("_")[0]) &&
          table.data.find((row) => row["reference"] === refValue)
        );
      if (!matchingTable) continue;

      if (!matchingTable.hasOwnProperty('columnUniqueCounts')) {
        matchingTable.columnUniqueCounts = columnUniqueCounts(matchingTable)
      }

      const refRows = matchingTable.data.reduce((acc, row) => {
        const filteredRowValues = Object.entries(row)
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
      break; // only need to find the first matching table
      }
  }

  return matchingRefValues
}

export function getTableDataFromRecords(filter_fn: (record: FeedbackRecord) => boolean): any[] {
  // filter_fn is a function that takes a record and returns true if it should be included in the table
  // returns an array of objects of the form {field: {refValue: {column: value, ...}, ...}, ...}
  let recordTables = useRecordFeedbackTaskViewModel({recordCriteria: null})?.records.records
    .filter(filter_fn)
    .map((rec) => {
      let answer_tables = rec?.answer?.value || {};
      if (answer_tables) {
        answer_tables = Object.fromEntries(
          Object.entries(answer_tables)
            .filter(([key, obj]) => {
              const value = (obj as { value: string }).value;
              return (typeof value === 'string') && (value.startsWith('{'))
            })
            .map(([key, obj]) => {
              try {
                const value = (obj as { value: string }).value;
                const table = JSON.parse(value);
                delete table.validation;
                return [key, table]
              } catch (e) {
                console.error(e);
                return [key, {}];
              }
            })
            .filter(([key, obj]) => Object.keys(obj).length > 0)
        )
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

      return {
        ...answer_tables, // ensures that answer tables are prioritized over field tables
        ...field_table,
      }
    })
    .filter((obj) => Object.keys(obj).length > 0);

  return recordTables;
}

export function columnSchemaToDesc(fieldName: string, validation: Validation, columnValidators: ColumnValidators): string | undefined {
  // tableJSON is an object of the form {data: [{column: value, ...}], validation: {columns: {column: panderaSchema, ...}}}
  // columnValidators is an object of the form {column: [validator, ...]}
  // returns a string describing the column schema and validators
  if (!validation) return;
  
  var desc = `<b>${fieldName}</b>: ` || "";
  if (validation.columns.hasOwnProperty(fieldName)) {
    const column = validation.columns[fieldName];
    desc += column.description || "";
  } else if (validation.index.find((index) => index.name === fieldName)) {
    const index = validation.index.find((index) => index.name === fieldName);
    desc += index.description || "";
  }

  if (columnValidators.hasOwnProperty(fieldName)) {
    const criteriaSpecs = columnValidators[fieldName]
      .map((value) => {
        let s = null;
        if (typeof value === "string") {
          s = value.replace('string', 'text');
          
        } else if (typeof value === "function") {
          s = `${value.name}`;

        } else if (typeof value === "object" && value?.type?.name) {
          s = `${value.type.name}`;

          if (value.parameters != null && typeof value.parameters !== 'object') {
            s += `: ${value.parameters}`;
          } else if (!['integer', 'decimal'].includes(value?.type?.name) && value.parameters != null && typeof value.parameters === 'object') {
            const parameters = JSON.stringify(value.parameters)
              .replace(/[{""}]/g, '').replace(/:/g, '=').replace(/,/g, ', ')
              .replace('=true', '').replace('column=', '');
            s += `(${parameters})`;
          }
        }
        return s;
      })
      .filter((value) => value != null);
    desc += `<br/><br/>Checks: ${criteriaSpecs.join(', ')}`
      .replace(/,/g, ", ").replace(/:/g, ": ");
  }

  return desc;
}


