import { useRecordFeedbackTaskViewModel } from '@/components/feedback-task/container/useRecordFeedbackTaskViewModel';


export function findMatchingRefValues(refValues, records) {
  const matchingRefValues = {};
  for (const [field, refValue] of Object.entries(refValues)) {
    for (const recordTables of records) {
      if (!recordTables) continue;
      const matchingTable = Object.values(recordTables)
        .find((table) => table.data.find((row) => row['reference'] === refValue));
      if (matchingTable) {
        if (!matchingTable.hasOwnProperty('columnUniqueCounts')) {
          matchingTable.columnUniqueCounts = columnUniqueCounts(matchingTable)
        }
        const refRows = matchingTable.data.reduce((acc, row) => {
          const filteredRowValues = Object.entries(row)
            .filter(([key, value]) => key != "reference" && (!matchingTable?.columnUniqueCounts?.hasOwnProperty(key) || matchingTable.columnUniqueCounts[key] > 1))
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
  }

  return matchingRefValues
}

export function columnUniqueCounts(tableJSON) {
  let uniqueCounts = {};
  for (let key of Object.keys(tableJSON.data[0])) {
    let values = tableJSON.data.map(row => row[key]);
    let filteredValues = values.filter(value => value !== null && value !== 'NA' && value !== '');
    uniqueCounts[key] = new Set(filteredValues).size;
  }

  return uniqueCounts;
}

export function getTableDataFromRecords(filter_fn) {
  let recordTables = useRecordFeedbackTaskViewModel({})?.records.records
    .filter(filter_fn)
    .map((rec) => {
      let answer_tables = rec?.answer?.value || {};
      if (answer_tables) {
        answer_tables = Object.fromEntries(
          Object.entries(answer_tables)
            .filter(([key, obj]) => typeof obj.value === 'string' && obj.value.startsWith('{'))
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
        .filter((value) => value !== undefined);
      desc += `<br/><br/>Checks: ${stringAndFunctionNames}`
        .replace(/,/g, ", ")
        .replace(/:/g, ": ");
    }
  }
  return desc;
}