import { type NuxtAxiosInstance } from "@nuxtjs/axios";

import { BackendExtractionRequest, BackendExtractionResponse } from "@/v1/domain/entities/extraction/Extraction";
import { Data, DataFrame, ReferenceValues } from "@/components/base/base-render-table/types";

const LLM_EXTRACTION_API_ERRORS = {
  ERROR_FETCHING_LLM_EXTRACTION: "ERROR_FETCHING_LLM_EXTRACTION",
};

export class GetLLMExtractionUseCase {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async completion(
    reference: string, 
    schema_name: string, 
    selectedRowData: Data,
    extractions: ReferenceValues, 
    columns?: Array<string>,
    headers?: Array<string>,
    types?: Array<string>,
    workspaceName?: string
  ): Promise<BackendExtractionResponse> {
    try {
      const params = this.createRequest(reference, schema_name, selectedRowData, extractions, columns, headers, types, workspaceName);
      const { data } = await this.axios.post<DataFrame>(
        `/v1/models/completion/${workspaceName}`, 
        params
      );

      return data;
    } catch (error) {
      throw {
        response: LLM_EXTRACTION_API_ERRORS.ERROR_FETCHING_LLM_EXTRACTION,
      }
    }
  }

  private createRequest(
    reference: string, 
    schema_name: string, 
    selectedRowData: Data,
    referenceValues: ReferenceValues, 
    columns?: Array<string>,
    headers?: Array<string>,
    types?: Array<string>,
    workspace?: string
  ): BackendExtractionRequest {

    var extractions: Record<string, Data> = Object.fromEntries(
      Object.entries(referenceValues).map(([schema_ref_field, dataframe]) => 
        [
          schema_ref_field.replace('_ref', ''), 
          Object.entries(dataframe)
            .filter(([key, value]) => selectedRowData.some(row => row[schema_ref_field] === key))
            .map(([key, value]) => ({
              reference: key,
              ...value
            }))
        ]
      )
    );

    extractions[schema_name] = selectedRowData;

    return {
      reference,
      schema_name,
      extractions,
      columns,
      headers,
      types,
      workspace,
    };
  }

}
