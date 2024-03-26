import { DataFrame, Validation, ValidationSpec, ValidationSpecs } from './types';
import { CellComponent } from "tabulator-tables";

type RecordDataFrames = Record<string, DataFrame>;
export type RecordDataFramesArray = RecordDataFrames[];


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

export function cellTooltip(e, cell: CellComponent, onRendered) {
  var message = null;
  let errors = cell._cell?.modules?.validate?.invalid;

  if (cell.getValue()?.length > 100) {
    message = cell.getValue() + '\n\n';
  }

  if (errors?.length > 0) {
    message = errors.map(stringifyCriteriaSpec).join(', ');
  }

  return message;
}




export function headerTooltip(e, column: CellComponent, onRendered, validation: Validation, columnValidators: ValidationSpecs) {
  try {
    const fieldName = column?.getDefinition()?.field;
    const desc = columnSchemaToDesc(fieldName, validation, columnValidators)

    if (!desc) return null;
    return desc;
  } catch (error) {
    console.log(error);
    console.log(error.stack);
  }
}

export function columnSchemaToDesc(fieldName: string, validation: Validation, columnValidators: ValidationSpecs): string | undefined {
  // tableJSON is an object of the form {data: [{column: value, ...}], validation: {columns: {column: panderaSchema, ...}}}
  // columnValidators is an object of the form {column: [validator, ...]}
  // returns a string describing the column schema and validators
  if (!validation || !fieldName) return;
  
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
      .map(stringifyCriteriaSpec)
      .filter((value) => value != null);
    desc += `<br/><br/>Checks: ${criteriaSpecs.join(', ')}`
      .replace(/,/g, ", ").replace(/:/g, ": ");
  }

  return desc;
}

function stringifyCriteriaSpec(value: ValidationSpec): string | null {
  let s = null;

  if (typeof value === 'string') {
    s = value.replace('string', 'text');

  } else if (typeof value === 'function') {
    s = `${value.name}`;

  } else if (typeof value === 'object' && value?.type?.name) {
    s = `${value.type.name}`;

    if (value?.parameters != null && typeof value.parameters !== 'object') {
      s += `: ${value.parameters}`;
    } else if (!['integer', 'decimal'].includes(value?.type?.name) && value.parameters != null && typeof value.parameters === 'object') {
      const parameters = JSON.stringify(value.parameters)
        .replace(/[{""}]/g, '').replace(/:/g, '=').replace(/,/g, ', ')
        .replace('=true', '').replace('column=', '');
      s += `(${parameters})`;
    }

  } else if (typeof value === 'object' && typeof value?.type === 'string') {
    if (value.type === "function") {
      s = JSON.stringify(value.parameters)
        .replace(/[{""}]/g, '').replace(/:/g, '=').replace(/,/g, ', ')
        .replace('=true', '').replace('column=', '');;
    } else {
      s = `${value.type}`;
    }
  }

  return s;
}

