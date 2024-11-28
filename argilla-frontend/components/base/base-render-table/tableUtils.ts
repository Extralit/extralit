import { CellComponent, ColumnComponent, GroupComponent, RangeComponent, RowComponent } from "tabulator-tables";
import { ReferenceValues } from "@/v1/domain/entities/table/TableData";
import { SuggestionCheck, ValidationSchema, Validator, Validators } from "@/v1/domain/entities/table/Validation";


export function isValidJSON(value: string): boolean {
  if (!value?.length || (!value.startsWith('{') && !value.startsWith('['))) { return false; }
  
  try {
    JSON.parse(value);
    return true;
  } catch (e) {
    console.log(e)
    return false;
  }
}

export function cellTooltip(e, cell: CellComponent, onRendered): string {
  var message = null;

  let errors = (cell as any)._cell?.modules?.validate?.invalid;

  if (cell.getValue()?.length > 100) {
    message = cell.getValue() + '\n\n';
  }

  if (errors?.length > 0) {
    message = errors.map(stringifyValidator).join(', ');
  }

  return message;
}



export function groupHeader(index: string, count: number, data: any, group: GroupComponent, referenceValues: ReferenceValues, refColumns: string[]) {
  const schema_ref = (group as any)._group.field
  let header = index
  let keyValues = '';
  if (referenceValues?.[schema_ref]?.hasOwnProperty(index)) {
    keyValues = Object.entries(referenceValues[schema_ref][index])
      // @ts-ignore
      .filter(([key, v]) => !!key && key !== "_id" && !refColumns?.includes(key) && v != null && v !== 'NA')
      .map(([key, v]) => `<span style="font-weight:normal; color:black; margin-left:0;">${key}:</span> ${v}`)
      .join(', ');
  }

  if (keyValues.length > 0) {
    header = `<small text="${index}">${keyValues}</small>`;
  } else {
    header = `<small style="color: red;">${index} (key not matched to ${schema_ref.replace(/_ref$/, '')})</small>`;
  }

  if (count > 1) header = header + `<small style='font-weight:normal; color:black; margin-left:10px;'>(${count})</small>`;
  return header;
}

export function headerTooltip(e, column: ColumnComponent, onRendered, validation: ValidationSchema, columnValidators: Validators) {
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

export function columnSchemaToDesc(
  fieldName: string, 
  validation: ValidationSchema, 
  columnValidators: Validators): string | undefined {
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
      .map(stringifyValidator)
      .filter((value) => value != null);
    desc += `<br/><br/>Checks: ${criteriaSpecs.join(', ')}`
      .replace(/,/g, ", ").replace(/:/g, ": ");
  }

  if (validation.columns[fieldName]?.checks?.multiselect?.delimiter) {
    desc += `, multivalues(delimiter="${validation.columns[fieldName]?.checks?.multiselect?.delimiter}")`
  }

  return desc;
}

function stringifyValidator(validator: Validator): string | null {
  let s = null;

  if (typeof validator === 'string') {
    s = validator.replace('string', 'text');
    if (validator.startsWith('regex:')) {
      s = `regex: "${regexToHumanReadable(validator.replace("regex:", ''))}"`;
    }

  } else if (typeof validator === 'function') {
    s = `${validator.name}`.replace('nullable', 'optional');

  } else if (typeof validator === 'object' && validator?.type?.name) {
    s = `${validator.type.name}`;
    if (validator?.parameters != null && typeof validator.parameters !== 'object') {
      s += `: ${validator.parameters}`;

    } else if (!['integer', 'decimal'].includes(validator?.type?.name) && validator.parameters != null && typeof validator.parameters === 'object') {
      const parameters = JSON.stringify(validator.parameters)
        .replace(/[{""}]/g, '').replace(/:/g, '=').replace(/,/g, ', ')
        .replace('=true', '').replace('column=', '');
      s += `(${parameters})`;
    }

  } else if (typeof validator === 'object' && typeof validator?.type === 'string') {
    if (validator.type === "function") {
      s = JSON.stringify(validator.parameters)
        .replace(/[{""}]/g, '').replace(/:/g, '=').replace(/,/g, ', ')
        .replace('=true', '').replace('column=', '');;
    } else {
      if (validator?.parameters != null && typeof validator.parameters !== 'object') {
        s += `: ${validator.parameters}`;
      }
    }
  }

  return s;
}

export function getRangeRowData(range: RangeComponent): Record<string, Record<string, any>> {
    const rangeData = range.getRows().reduce((acc, row: RowComponent) => {
        acc[row.getIndex()] = row.getData();
        return acc;
      }, {});

    return rangeData;
  };

export function getRangeColumns(range: RangeComponent): string[] {
  const columns = range.getColumns().map((col) => col.getField());
  return columns;
}

function regexToHumanReadable(regex: string): string {
  // Replace regex patterns with example strings
  let example = regex;
  
  example = example.replace(/\\d/g, '1');
  example = example.replace(/\\w/g, 'a');
  example = example.replace(/\\s/g, ' ');

  example = example.replace(/[\^\$\.\*\+\?\{\}\[\]\\\(\)]/g, '');

  return example;
}


function getListAutocompleteValues(values: SuggestionCheck): any[] {
  let editorParamsValues: any[] = [];

  if (Array.isArray(values)) {
    editorParamsValues = values.map((value) => ({ label: value, value: value, data: {} }));

  } else if (typeof values === 'object') {
    editorParamsValues = Object.entries(values)
      .map(([key, value]) => ({ label: key, value: key, data: value }));
  }
  return editorParamsValues;
}


export function getColumnEditorParams(
  fieldName: string,
  validation: ValidationSchema,
  refColumns: string[],
  referenceValues: ReferenceValues,
): any {
  let config: any = { editorParams: {} };

  if (validation?.columns?.hasOwnProperty(fieldName)) {
    const columnValidators = validation.columns[fieldName];
    const suggestions = columnValidators?.checks?.suggestion;
    const isinValues = columnValidators?.checks?.isin;

    if (columnValidators?.dtype === "str") {
      config.editor = "list";
      config.editorParams.emptyValue = "NA";
      config.editorParams.autocomplete = true;
      config.editorParams.freetext = true;
      config.editorParams.listOnEmpty = true;
      config.editorParams.selectContents = true;
      config.editorParams.valuesLookupField = fieldName;

      if (isinValues) {
        const allowedValues = getListAutocompleteValues(isinValues);
        if (allowedValues.length) {
          config.editorParams.valuesLookup = (cell: CellComponent, filterTerm: string) => {
            return allowedValues
          }
        }

      } else if (suggestions) {
        let suggestionValues: any[] = getListAutocompleteValues(suggestions);

        if (suggestionValues.length) {
          config.editorParams.valuesLookup = (cell: CellComponent, filterTerm: string) => {
            let values = cell.getColumn().getCells()
              .map((c) => c.getValue())
              .filter(value => value != null && value !== 'NA' && !suggestionValues.some(item => item.value === value))

            return [...new Set(values), ...suggestionValues]
          }
        } else {
          config.editorParams.valuesLookup = 'active';
        }
      }

      if (columnValidators.checks?.multiselect?.delimiter) {
        if (isinValues) {
          config.editorParams.multiselect = true;
          config.editorParams.autocomplete = false;
        }
      }

    } else if (columnValidators.dtype.includes("int") || columnValidators.dtype.includes("float")) {
      config.hozAlign = "right";
      config.editorParams.valuesLookup = 'active';
      config.editorParams.valuesLookupField = fieldName;
    }

  } else if (refColumns?.includes(fieldName)) {
    config.editor = "list";

    if (referenceValues?.hasOwnProperty(fieldName)) {
      config.editorParams = {
        allowEmpty: true,
        listOnEmpty: true,
        freetext: true,
        emptyValue: null,
        valuesLookup: false,
        values: Object.entries(referenceValues[fieldName]).map(
          ([key, value]) => ({ label: key, value: key, data: value })
        ),
      };

    } else {
      // Default editor params for reference columns
      config.editorParams = {
        search: true,
        valuesLookup: 'active',
        listOnEmpty: true,
        freetext: true,
      };
    }
  }

  const hasSuggestedValues = config.editorParams?.values || typeof config.editorParams?.valuesLookup == 'function';
  if (hasSuggestedValues) {
    config.editorParams.itemFormatter = function (label, value, item, element) {
      if (item.data && typeof item.data === 'object') {
        const keyValues = Object.entries(item.data)
          .filter(([key, v]) => v !== 'NA' && v !== null)
          .map(([key, v]) => `<span style="font-weight:normal; color:black; margin-left:0;">${key}:</span> ${v}`)
          .join(', ');

        return `<strong>${label}</strong>${keyValues ? `: ${keyValues}` : ''}`;
      }
      return label;
    };

    config.editorParams.maxWidth = '500px'

    config.editorParams.filterFunc = function (term: string, label: string, value, item) {
      if (String(label).startsWith(term) || value.includes(term)) {
        return true;
      } else if (term.length >= 3 && item.data) {
        return JSON.stringify(item.data).toLowerCase().match(term.toLowerCase());
      }
      return label === term;
    };

    config.editorParams.placeholderEmpty = "Type to search by keyword...";
  }

  return config;
}

