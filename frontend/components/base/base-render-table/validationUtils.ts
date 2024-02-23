var integer = (cell: any, value: string, parameters: { nullable: boolean }): boolean => 
	(parameters.nullable && value == "NA") || /^-?\d+$/.test(value);
var decimal = (cell: any, value: string, parameters: { nullable: boolean }): boolean => 
	(parameters.nullable && value == "NA") || /^-?\d*(\.\d+)?$/.test(value);
var greater_equal = (cell: any, value: string, parameters: number): boolean => 
	value == "NA" || parseFloat(value) >= parameters;
var less_equal = (cell: any, value: string, parameters: number): boolean => 
	value == "NA" || parseFloat(value) <= parameters;

type SchemaColumns = {
	[columnName: string]: {
		required: boolean;
		dtype: string;
		nullable: boolean;
		unique: boolean;
		checks: any;
	};
};

export function getColumnValidators(tableJSON: any): any {
	const schemaColumns: SchemaColumns = tableJSON.validation?.columns; // Pandera yaml schema
	if (schemaColumns == null) return {};
	const tableColumns = tableJSON.schema.fields.map((col) => col.name);
	
	const tabulatorValidators = {};
	for (const [columnName, columnSchema] of Object.entries(schemaColumns)) {
		if (!tableColumns.includes(columnName)) continue;
		const validators = [];

		if (columnSchema.required) {
			validators.push("required");
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
			} else if (key === "isin" && value.length) {
				validators.push(`in:${[...value, "NA"].join("|")}`);
			}
		}

		// Custom validator example for unique check
		if (columnSchema.unique) {
			const uniqueValidator = {
				type: function (cell: any, value: string, parameters: any): boolean {
					const columnValues = cell
					.getTable()
					.getData()
					.map((row) => row[cell.getField()]);
						return columnValues.filter((v) => v === value).length === 1;
					},
			};
			validators.push(uniqueValidator);
		}
		tabulatorValidators[columnName] = validators;
	}

	return tabulatorValidators;
}
