import { DataFrameSchema } from "./Schema";
import { type Data } from "./TableData";

export interface BackendExtractionRequest {
  reference: string;
  schema_name: string;
  extractions: Record<string, Data>;
  columns?: Array<string>;
  headers?: Array<string>;
  types?: Array<string>;
  prompt?: string;
}

export interface BackendExtractionResponse {
  schema: DataFrameSchema;
  data: Data;
}
