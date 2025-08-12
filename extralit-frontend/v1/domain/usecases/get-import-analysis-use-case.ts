import { type NuxtAxiosInstance } from "@nuxtjs/axios";

import {
  ImportAnalysisRequest,
  ImportAnalysisResponse,
  DocumentMetadata,
  FileInfo,
  DataframeData,
} from "~/v1/domain/entities/import/ImportAnalysis";

const IMPORT_ANALYSIS_API_ERRORS = {
  ERROR_FETCHING_IMPORT_ANALYSIS: "ERROR_FETCHING_IMPORT_ANALYSIS",
};

export class GetImportAnalysisUseCase {
  constructor(private readonly axios: NuxtAxiosInstance) {}

  async analyzeImport(
    workspaceId: string,
    dataframeData: DataframeData,
    matchedFiles: any[]
  ): Promise<ImportAnalysisResponse> {
    try {
      const request = this.createAnalysisRequest(workspaceId, dataframeData, matchedFiles);

      const { data } = await this.axios.post<ImportAnalysisResponse>("/v1/imports/analyze", request);

      return data;
    } catch (error) {
      let errorMessage = error.message || "Unknown error occurred";

      if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      } else if (error.response?.status) {
        errorMessage = `HTTP ${error.response.status}: ${error.response.statusText || "Request failed"}`;
      }

      throw {
        response: IMPORT_ANALYSIS_API_ERRORS.ERROR_FETCHING_IMPORT_ANALYSIS,
        message: errorMessage,
      };
    }
  }

  private createAnalysisRequest(
    workspaceId: string,
    dataframeData: DataframeData,
    matchedFiles: any[]
  ): ImportAnalysisRequest {
    const documents: Record<string, DocumentMetadata> = {};

    // Create a map of filename to file info for quick lookup
    const fileInfoMap: Record<string, { file: File; reference: string }> = {};
    if (matchedFiles && matchedFiles.length > 0) {
      matchedFiles.forEach((matchedFile) => {
        const filename = matchedFile.file.name;
        const reference = matchedFile.bibEntry?.reference;
        if (filename && reference) {
          fileInfoMap[filename] = {
            file: matchedFile.file,
            reference,
          };
        }
      });
    }

    // Convert dataframe data to document metadata
    dataframeData.data.forEach((row: Record<string, any>) => {
      const reference = row.reference || row.key;
      if (!reference) return;

      // Extract file information for this reference from matched files
      const filePaths = row.filePaths || [];
      const associatedFiles: FileInfo[] = [];

      // Find files that match this reference
      Object.entries(fileInfoMap).forEach(([filename, fileInfo]) => {
        if (fileInfo.reference === reference || filePaths.includes(filename)) {
          associatedFiles.push({
            filename,
            size: fileInfo.file.size || 0,
          });
        }
      });

      // Also check for files directly in filePaths that might not be in matched files
      filePaths.forEach((filename: string) => {
        if (!associatedFiles.find((f) => f.filename === filename)) {
          // Try to find the file in matched files by filename
          const matchedFile = matchedFiles.find((mf) => mf.file.name === filename);
          if (matchedFile) {
            associatedFiles.push({
              filename,
              size: matchedFile.file.size || 0,
            });
          } else {
            // Add with unknown size if we can't find the file
            associatedFiles.push({
              filename,
              size: 0,
            });
          }
        }
      });

      documents[reference] = {
        document_create: {
          reference,
          doi: row.doi,
          pmid: row.pmid,
          workspace_id: workspaceId,
        },
        associated_files: associatedFiles,
      };
    });

    return {
      workspace_id: workspaceId,
      documents,
    };
  }
}
