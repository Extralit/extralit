import { type NuxtAxiosInstance } from "@nuxtjs/axios";

import {
  ImportAnalysisRequest,
  ImportAnalysisResponse,
  DocumentMetadata,
  FileInfo
} from "~/v1/domain/entities/import/ImportAnalysis";
import { DataframeData } from "~/v1/domain/entities/import/ImportAnalysis";

const IMPORT_ANALYSIS_API_ERRORS = {
  ERROR_FETCHING_IMPORT_ANALYSIS: "ERROR_FETCHING_IMPORT_ANALYSIS",
};

export class GetImportAnalysisUseCase {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async analyzeImport(
    workspaceId: string,
    dataframeData: DataframeData,
    pdfFiles?: File[]
  ): Promise<ImportAnalysisResponse> {
    try {
      const request = this.createAnalysisRequest(workspaceId, dataframeData, pdfFiles);

      console.log(request)

      const { data } = await this.axios.post<ImportAnalysisResponse>(
        `/v1/imports/analyze`,
        request
      );

      return data;

    } catch (error) {
      console.log('Import analysis error:', error);
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
        response: IMPORT_ANALYSIS_API_ERRORS.ERROR_FETCHING_IMPORT_ANALYSIS,
        message: errorMessage
      };
    }
  }

  private createAnalysisRequest(
    workspaceId: string,
    dataframeData: DataframeData,
    pdfFiles?: File[]
  ): ImportAnalysisRequest {
    const documents: Record<string, DocumentMetadata> = {};

    const fileNameMap: Record<string, File> = {};
    if (pdfFiles && pdfFiles.length > 0) {
      pdfFiles.forEach(file => {
        fileNameMap[file.name] = file;
      });
    }

    // Convert dataframe data to document metadata
    dataframeData.data.forEach((row: Record<string, any>) => {
      const reference = row.reference || row.key;
      if (!reference) return;

      // Extract file information for this reference
      const filePaths = row.filePaths || [];
      const associatedFiles: FileInfo[] = filePaths.map((filename: string) => {
        const fileObj = fileNameMap[filename];
        return {
          filename,
          size: fileObj?.size,
        };
      });

      documents[reference] = {
        document_create: {
          reference: reference,
          doi: row.doi,
          pmid: row.pmid,
          workspace_id: workspaceId,
        },
        associated_files: associatedFiles
      };
    });

    return {
      workspace_id: workspaceId,
      documents
    };
  }

  private extractMetadata(row: Record<string, any>): Record<string, any> {
    // Extract additional metadata fields not covered by DocumentCreate
    const excludedFields = [
      'reference', 'title', 'authors', 'year', 'journal', 'volume',
      'pages', 'doi', 'url', 'abstract', 'keywords', 'pmid', 'filePaths'
    ];

    const metadata: Record<string, any> = {};
    Object.keys(row).forEach(key => {
      if (!excludedFields.includes(key) && row[key] !== undefined && row[key] !== null && row[key] !== '') {
        metadata[key] = row[key];
      }
    });

    return Object.keys(metadata).length > 0 ? metadata : undefined;
  }
}