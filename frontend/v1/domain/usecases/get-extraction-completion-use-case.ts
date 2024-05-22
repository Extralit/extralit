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
    workspaceName: string,
    selectedRowData: Data,
    extractions: ReferenceValues, 
    columns?: Array<string>,
    headers?: Array<string>,
    types?: Array<string>,
    prompt?: string,
  ): Promise<BackendExtractionResponse> {
    try {
      const json = this.createRequest(reference, schema_name, selectedRowData, extractions, columns, headers, types, prompt);
      const params = { workspace: workspaceName };
      
      const { data } = await this.axios.post<DataFrame>(
        `/v1/models/completion`, json, { params: params }
      );

      return data;
    } catch (error) {
      let errorMessage = error.message;
      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.response?.data) {
        errorMessage = error.response.data;
      } else if (error.response) {
        errorMessage = error.response;
      }

      throw {
        response: LLM_EXTRACTION_API_ERRORS.ERROR_FETCHING_LLM_EXTRACTION,
        message: errorMessage
      }
    }
  }

  private createRequest(
    reference: string, 
    schema_name: string, 
    selectedRowData: Data,
    referenceValues?: ReferenceValues, 
    columns?: Array<string>,
    headers?: Array<string>,
    types?: Array<string>,
    prompt?: string
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
    if (!extractions) {
      extractions = {};
    }

    extractions[schema_name] = selectedRowData;

    if (prompt) {
      prompt = prompt.trim();
      if (prompt === '') {
        prompt = null;
      }
    }

    return {
      reference,
      schema_name,
      extractions,
      columns,
      headers,
      types,
      prompt,
    };
  }

}
