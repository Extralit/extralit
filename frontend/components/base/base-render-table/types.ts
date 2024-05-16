export interface DataFrameSchema {
  fields: {
    name: string;
    type: string;
    extDtype?: string;
  }[];
  primaryKey: string[];
}

export interface SchemaMetadata {
  schemaName?: string;
  etag?: string;
  version_id?: string;
  last_modified?: Date;
  version_tag?: string;
}

export type DataFrameSchemaWithMetadata = DataFrameSchema & SchemaMetadata;
export interface Data extends Array<{[field: string]: any}> {}

export interface DataFrame {
  data: Data;
  schema: DataFrameSchemaWithMetadata;
  reference?: string;
  validation?: PanderaSchema;
  columnUniqueCounts?: Record<string, number>;
};

export interface PanderaSchema {
  name: string;
  columns: SchemaColumns;
  index: SchemaIndexColumns[];
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
  isin?: SuggestionCheck;
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

export type ReferenceValues = Record<string, Record<string, Data>>;
