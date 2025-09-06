// Pandera schema types for TypeScript

export interface PanderaColumn {
  dtype: string;
  nullable?: boolean;
  unique?: boolean;
  coerce?: boolean;
  checks?: string[];
  name?: string;
}

export interface PanderaDataFrameSchema {
  schema_type: "DataFrameSchema";
  version: string;
  columns: Record<string, PanderaColumn>;
  checks?: string[];
  index?: any;
  dtype?: string;
  coerce?: boolean;
  strict?: boolean;
  name?: string;
  ordered?: boolean;
  unique?: boolean;
  report_duplicates?: boolean;
  unique_column_names?: boolean;
  add_missing_columns?: boolean;
  title?: string;
  description?: string;
}

export interface PanderaSeriesSchema {
  schema_type: "SeriesSchema";
  dtype: string;
  name?: string;
  nullable?: boolean;
  unique?: boolean;
  coerce?: boolean;
  checks?: string[];
  metadata?: any;
  description?: string;
  title?: string;
}

export type PanderaSchema = PanderaDataFrameSchema | PanderaSeriesSchema;

export interface PanderaSchemaValidationResult {
  isValid: boolean;
  errors?: string[];
}

// Utility functions for Pandera schema validation
export function validatePanderaSchema(schema: any): PanderaSchemaValidationResult {
  if (!schema || typeof schema !== 'object') {
    return { isValid: false, errors: ['Schema must be an object'] };
  }

  // Check for required fields based on schema type
  if (schema.schema_type === 'SeriesSchema') {
    if (!schema.dtype) {
      return { isValid: false, errors: ['SeriesSchema must have a dtype field'] };
    }
  } else if (schema.schema_type === 'DataFrameSchema') {
    if (!schema.columns && !schema.index) {
      return { isValid: false, errors: ['DataFrameSchema must have columns or index field'] };
    }
  } else if (schema.columns) {
    // Assume it's a DataFrame schema if it has columns
    return { isValid: true };
  } else {
    return { isValid: false, errors: ['Invalid Pandera schema format'] };
  }

  return { isValid: true };
}

export function createEmptyDataFrameSchema(): PanderaDataFrameSchema {
  return {
    schema_type: "DataFrameSchema",
    version: "0.21.1",
    columns: {},
    checks: [],
    coerce: false,
    strict: true,
    name: null,
    ordered: false,
    unique: false,
    report_duplicates: false,
    unique_column_names: true,
    add_missing_columns: false,
  };
}

export function createEmptySeriesSchema(): PanderaSeriesSchema {
  return {
    schema_type: "SeriesSchema",
    dtype: "str",
    nullable: true,
    unique: false,
    coerce: false,
    checks: [],
  };
}