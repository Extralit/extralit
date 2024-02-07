import { useRecordFeedbackTaskViewModel } from '@/components/feedback-task/container/useRecordFeedbackTaskViewModel';


export function isTableJSON(value) {
  if (!value?.length || (!value.startsWith('{') && !value.startsWith('['))) { return false; }
  
  try {
    JSON.parse(value);
    return true;
  } catch (e) {
    console.log(e)
    return false;
  }
}

export function columnUniqueCounts(tableJSON) {
  // tableJSON is an object of the form {data: [{column: value, ...}, ...]}
  // returns an object of the form {column: uniqueCount, ...}
  let uniqueCounts = {};
  for (let key of Object.keys(tableJSON.data[0])) {
    let values = tableJSON.data.map(row => row[key]);
    let filteredValues = values.filter(value => value != null && value !== 'NA' && value?.length);
    uniqueCounts[key] = new Set(filteredValues).size;
  }

  return uniqueCounts;
}

export function getMaxStringValue(columnName, data) {
  return data.reduce((max, row) => row[columnName] > max ? row[columnName] : max, "");
}

export function incrementReferenceStr(reference) {
  const parts = reference.split("-");
  const lastPart = parts[parts.length - 1];
  const suffix = lastPart.slice(-1);
  const incrementedDigits = String(parseInt(lastPart) + 1).padStart(lastPart.length - suffix.length, '0');
  const newReference = `${parts.slice(0, -1).join("-")}-${incrementedDigits}${suffix}`;

  return newReference;
}

export function findMatchingRefValues(refValues, records) {
  // refValues is an object of the form {field: refValue}
  // records is an array of objects of the form {table_name: {data: [{reference: refValue, ...}, ...]}}
  // returns an object of the form {field: {refValue: {column: value, ...}, ...}, ...}
  const matchingRefValues = {};

  for (const [field, refValue] of Object.entries(refValues)) {
    for (const recordTables of records) {
      if (!recordTables) continue;
      const matchingTable = Object.values(recordTables)
        .find((table) => table.data.find((row) => row["reference"] === refValue));
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
      break;
      }
  }

  return matchingRefValues
}

export function getTableDataFromRecords(filter_fn) {
  // filter_fn is a function that takes a record and returns true if it should be included in the table
  // returns an array of objects of the form {field: {refValue: {column: value, ...}, ...}, ...}
  let recordTables = useRecordFeedbackTaskViewModel({})?.records.records
    .filter(filter_fn)
    .map((rec) => {
      let answer_tables = rec?.answer?.value || {};
      if (answer_tables) {
        answer_tables = Object.fromEntries(
          Object.entries(answer_tables)
            .filter(([key, obj]) => {
              return (typeof obj.value === 'string') && (obj.value.startsWith('{'))
            })
            .map(([key, obj]) => {
              try {
                const table = JSON.parse(obj.value);
                delete table.validation;
                return [key, table]
              } catch (e) {
                console.error(e);
                return [key, {}];
              }
            }).filter(([key, obj]) => Object.keys(obj).length > 0)
        )
      }

      let field_table = rec.fields
        .filter((field) => field?.settings?.use_table && field?.content.startsWith('{'))
        .reduce((acc, field) => {
          try {
            acc[field.name] = JSON.parse(field.content);
            delete acc[field.name].validation;
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

export function columnSchemaToDesc(fieldName, tableJSON, columnValidators) {
  // tableJSON is an object of the form {data: [{column: value, ...}], validation: {columns: {column: panderaSchema, ...}}}
  // columnValidators is an object of the form {column: [validator, ...]}
  // returns a string describing the column schema and validators
  if (!tableJSON) return;
  
  var desc;
  if (tableJSON?.validation?.columns.hasOwnProperty(fieldName)) {
    const panderaSchema = tableJSON?.validation.columns[fieldName];
    desc = panderaSchema.description;

    if (columnValidators.hasOwnProperty(fieldName)) {
      const stringAndFunctionNames = columnValidators[fieldName]
        .map((value) => {
          if (typeof value === "string") {
            return value;
          } else if (typeof value === "function") {
            return value.name;
          } else if (typeof value === "object" && value?.type?.name) {
            return value?.parameters != null
              ? `${value.type.name}: ${JSON.stringify(value.parameters)}`
              : `${value.type.name}`;
          }
        })
        .filter((value) => value != null);
      desc += `<br/><br/>Checks: ${stringAndFunctionNames}`
        .replace(/,/g, ", ")
        .replace(/:/g, ": ");
    }
  }
  return desc;
}