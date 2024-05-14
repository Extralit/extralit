import { Data, DataFrameSchema } from "@/components/base/base-render-table/types";

export interface BackendExtractionRequest {
  reference: string;
  schema_name: string;
  extractions: Record<string, Data>;
  columns?: Array<string>;
  headers?: Array<string>;
  types?: Array<string>;
  workspace?: string;
}


export interface BackendExtractionResponse {
    schema: DataFrameSchema;
    data: Data;
}
