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

export class ImportAnalysisUseCase {
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

      const { data } = await this.axios.post<ImportAnalysisResponse>(
        `/api/v1/imports/analyze`,
        request
      );

      console.log(data)

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

    // Convert dataframe data to document metadata
    dataframeData.data.forEach((row: Record<string, any>) => {
      const reference = row.reference || row.key;
      if (!reference) return;

      // Extract file information for this reference
      const associatedFiles: FileInfo[] = [];
      const filePaths = row.filePaths || [];

      // Match PDF files to this reference
      if (pdfFiles && filePaths.length > 0) {
        filePaths.forEach((filePath: string) => {
          const matchingFile = pdfFiles.find(file =>
            file.name.includes(filePath) || filePath.includes(file.name)
          );

          if (matchingFile) {
            associatedFiles.push({
              filename: matchingFile.name,
              size: matchingFile.size
            });
          } else {
            // Include file info even if PDF not found (for analysis)
            associatedFiles.push({
              filename: filePath,
              size: 0 // Unknown size
            });
          }
        });
      }

      documents[reference] = {
        document_create: {
          title: row.title,
          authors: Array.isArray(row.authors) ? row.authors : [row.authors].filter(Boolean),
          year: String(row.year || ''),
          journal: row.journal,
          volume: row.volume,
          pages: row.pages,
          doi: row.doi,
          url: row.url,
          abstract: row.abstract,
          keywords: row.keywords ? (Array.isArray(row.keywords) ? row.keywords : [row.keywords]) : undefined,
          reference,
          pmid: row.pmid,
          workspace_id: workspaceId,
          metadata: this.extractMetadata(row)
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