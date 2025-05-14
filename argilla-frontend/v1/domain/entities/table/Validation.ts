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

export type SchemaIndexColumns = {
  name: string;
  required: boolean;
  description: string;
  dtype: string;
  nullable: boolean;
  unique: boolean;
  checks: any;
};

export interface ValidationSchema {
  name: string;
  columns: SchemaColumns;
  index: SchemaIndexColumns[];
  checks?: Checks;
};

export type Checks = {
  check_less_than?: ColumnsConsistencyCheck;
  check_greater_than?: ColumnsConsistencyCheck;
  check_between?: ColumnsConsistencyCheck;
  isin?: SuggestionCheck;
  suggestion?: SuggestionCheck;
  multiselect?: MultiselectCheck;
};

export type Validator = string | CallableFunction | { type: (cell: any, value: string, parameters: any) => boolean; parameters?: any };
export type Validators = Record<string, Validator[]>;

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

