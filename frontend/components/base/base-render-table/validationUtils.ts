import { CellComponent } from "tabulator-tables";
import { DataFrame, SchemaColumns, Checks, PanderaSchema, Validator, Validators, ReferenceValues, SuggestionCheck } from "./types";

var integer = (cell: any, value: string, parameters: { nullable: boolean }): boolean => 
	(parameters.nullable && value == "NA") || /^-?\d+$/.test(value);
var decimal = (cell: any, value: string, parameters: { nullable: boolean }): boolean => 
	(parameters.nullable && value == "NA") || /^-?\d*(\.\d+)?$/.test(value);
var greater_equal = (cell: any, value: string, parameters: number): boolean => 
	value == null || value == "NA" || parseFloat(value) >= parameters;
var less_equal = (cell: any, value: string, parameters: number): boolean => 
	value == null || value == "NA" || parseFloat(value) <= parameters;

var unique = (cell: any, value: string, parameters: any): boolean => {
  const columnValues = cell
    .getTable()
    .getData()
    .map((row) => row[cell.getField()]);
  return columnValues.filter((v) => v === value).length === 1;
};
	
var less_than = (cell: any, value: any, parameters: { column: string, or_equal: boolean }): boolean => {
  const rowData = cell.getRow().getData();
  const other = rowData[parameters.column];
	if (value == null || other == null) return true;
	if (value == "NA" || other == "NA") return true;

  return (parameters.or_equal ? parseFloat(value) <= parseFloat(other) : parseFloat(value) < parseFloat(other));
};

var greater_than = (cell: any, value: any, parameters: { column: string, or_equal: boolean }): boolean => {
  const rowData = cell.getRow().getData();
  const other = rowData[parameters.column];
	if (value == null || other == null) return true;
	if (value == "NA" || other == "NA") return true;

  return (parameters.or_equal ? parseFloat(value) >= parseFloat(other) : parseFloat(value) > parseFloat(other));
};

var between = (cell: any, value: any, parameters: { lower: string, upper: string, or_equal: boolean }): boolean => {
  const row = cell.getRow().getData();
	if (value == null || row[parameters.lower] == null || row[parameters.upper] == null) return true;
	if (value == "NA" || row[parameters.lower] == "NA" || row[parameters.upper] == "NA") return true;

  value = parseFloat(value);
  const value_lower = parseFloat(row[parameters.lower]);
  const value_upper = parseFloat(row[parameters.upper]);
  return (parameters.or_equal ? 
      value >= value_lower && value <= value_upper :
      value > value_lower && value < value_upper
    );
};

/**
 * Retrieves the Tabulator validators based on the provided Pandera DataFrameSchema serialized json.
 * 
 * @param tableJSON - The table JSON containing the validation information.
 * @returns An object containing the column validators.
 */
export function getColumnValidators(tableJSON: DataFrame, validation: PanderaSchema): Validators {
	const schemaColumns = validation?.columns;
	const indexColumns: SchemaColumns = validation?.index
    .reduce((acc, curr) => ({ ...acc, [curr.name]: curr }), {}) || {};
	if (schemaColumns == null) return {};
	const tableColumns = tableJSON.schema.fields.map((col) => col.name);
	
	const columnValidators: Validators = {};
	for (const [columnName, columnSchema] of Object.entries({...schemaColumns, ...indexColumns})) {
		if (!tableColumns.includes(columnName)) continue;
		const validators: Validator[] = [];

		if (columnSchema.required) {
			validators.push("required");
		}

		if (columnSchema.unique) {
			validators.push('unique');
		}

		if (columnSchema.dtype === "str") {
			validators.push("string");
		} else if (columnSchema.dtype.includes("int")) {
			validators.push({ type: integer, parameters: { nullable: columnSchema.nullable } });
		} else if (columnSchema.dtype.includes("float")) {
			validators.push({ type: decimal, parameters: { nullable: columnSchema.nullable } });
		}

		for (const key in columnSchema?.checks) {
			const value = columnSchema.checks[key];

			if (key === "greater_than_or_equal_to") {
				validators.push({ type: greater_equal, parameters: value });

			} else if (key === "less_than_or_equal_to") {
				validators.push({ type: less_equal, parameters: value });

			} else if (key === "isin" && value != null) {
        if (Array.isArray(value) && value.length) {
          validators.push(`in:${[...value].join("|")}`);
        } else if (typeof value === 'object' && value !== null) {
          validators.push(`in:${[...Object.keys(value)].join("|")}`);
        }
			} else if (key === "str_matches" && value != null) {
        validators.push(`regex:${value}`);
      }
		}

		columnValidators[columnName] = validators;
	}

	addDataFrameChecks(validation.checks, columnValidators);
	return columnValidators;
}


/**
 * Adds dataframe-level checks to the column validators.
 * 
 * @param checks - The checks to be added.
 * @param columnValidators - The column validators to add the checks to.
 */
function addDataFrameChecks(checks: Checks, columnValidators: Validators) {
  if (checks?.check_less_than && Object.values(checks.check_less_than).every(Array.isArray)) {
    checks.check_less_than.columns_a.forEach((columnName, index) => {
			if (!columnValidators[columnName]) {
        columnValidators[columnName] = [];
      }			
      columnValidators[columnName].push({
        type: less_than,
        parameters: {
          column: checks.check_less_than.columns_b[index],
          or_equal: checks.check_less_than.or_equal[index]
        }
      });
    });
  }

  if (checks?.check_greater_than && Object.values(checks.check_greater_than).every(Array.isArray)) {
    checks.check_greater_than.columns_a.forEach((columnName, index) => {
			if (!columnValidators[columnName]) {
        columnValidators[columnName] = [];
      }
      columnValidators[columnName].push({
        type: greater_than,
        parameters: {
          column: checks.check_greater_than.columns_b[index],
          or_equal: checks.check_greater_than.or_equal[index]
        }
      });
    });
  }

  if (checks?.check_between && Object.values(checks.check_between).every(Array.isArray)) {
    checks.check_between.columns_target.forEach((columnName, index) => {
			if (!columnValidators[columnName]) {
        columnValidators[columnName] = [];
      }
      columnValidators[columnName].push({
        type: between,
        parameters: {
          lower: checks.check_between.columns_lower[index],
          upper: checks.check_between.columns_upper[index],
          or_equal: checks.check_between.or_equal[index]
        }
      });
    });
  }
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
  validation: PanderaSchema,
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
      config.editorParams.clearable = true;
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
          ([key, value]) => ({ label: key, value: key, data: value})
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

    config.editorParams.filterFunc = function (term, label, value, item) {
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

