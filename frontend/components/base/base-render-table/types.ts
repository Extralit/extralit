export interface DataFrame {
  data: Record<string, any>[];
  schema: {
    fields: { name: string, type: string, extDtype: string }[];
    primaryKey: string[];
  };
  reference?: string;
  validation?: PanderaSchema;
  columnUniqueCounts?: Record<string, number>;
};


export interface PanderaSchema {
  columns: SchemaColumns;
  index: SchemaIndexColumns[];
  name: string;
  checks?: Checks;
};

export type SchemaColumns = {
	[columnName: string]: {
		required: boolean;
    description: string;
		dtype: string;
		nullable: boolean;
		unique: boolean;
		checks: Checks;
	};
};

export type Checks = {
  check_less_than?: ColumnsConsistencyCheck;
  check_greater_than?: ColumnsConsistencyCheck;
  check_between?: ColumnsConsistencyCheck;
  isin?: string[];
  suggestion?: SuggestionCheck;
  multiselect?: MultiselectCheck;
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

export type SuggestionCheck = string[] | {
  [columnName: string]: {} | {
    [otherColumnName: string]: [otherColumnValue: string];
  };
};

export type ColumnsConsistencyCheck = {
  columns_a?: string[];
  columns_b?: string[];
  columns_target?: string[];
  columns_lower?: string[];
  columns_upper?: string[];
  or_equal?: boolean[];
};

export type MultiselectCheck = {
  delimiter?: string;
  isin?: string[];
}

export type Validator = string | CallableFunction | { type: (cell: any, value: string, parameters: any) => boolean; parameters?: any };
export type Validators = Record<string, Validator[]>;

export type ReferenceValues = Record<string, Record<string, Record<string, any>>>;
