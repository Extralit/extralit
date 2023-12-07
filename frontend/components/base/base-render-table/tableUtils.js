

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