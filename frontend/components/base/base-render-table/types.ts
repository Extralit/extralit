export type DataFrame = {
  data: Record<string, any>[];
  schema: {
    fields: { name: string, type: string, extDtype: string }[];
    primaryKey: string[];
  };
  reference?: string;
  validation?: Validation;
  columnUniqueCounts?: Record<string, number>;
};

export type Validation = {
  columns: SchemaColumns;
  index: SchemaIndexColumns[];
  name: string;
  checks?: Record<string, Check>;
};

export type Check = {
  columns_a?: string[];
  columns_b?: string[];
  columns_target?: string[];
  columns_lower?: string[];
  columns_upper?: string[];
  or_equal?: boolean[];
};

export type SchemaColumns = {
	[columnName: string]: {
		required: boolean;
    description: string;
		dtype: string;
		nullable: boolean;
		unique: boolean;
		checks: any;
	};
};


export type SchemaIndexColumns = {
  name: string;
  required: boolean;
  description: string;
  dtype: string;
  nullable: boolean;
  unique: boolean;
  checks: any;
};


export type Validator = string | CallableFunction | { type: (cell: any, value: string, parameters: any) => boolean; parameters?: any };
export type ColumnValidators = Record<string, Validator[]>;
