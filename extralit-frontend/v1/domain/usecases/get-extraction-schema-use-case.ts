import type { AxiosInstance, AxiosHeaders } from "axios";
import { type FileMetadata } from "../entities/table/Schema";
import { type ValidationSchema } from "../entities/table/Validation";

const FILES_API_ERRORS = {
  ERROR_FETCHING_SCHEMA_FILE: "ERROR_FETCHING_SCHEMA_FILE",
};

export class GetExtractionSchemaUseCase {
  constructor(private readonly axios: AxiosInstance) {}

  async fetch(
    workspaceName: string,
    schemaName: string,
    versionId?: string
  ): Promise<[ValidationSchema, FileMetadata]> {
    try {
      const url = `/v1/file/${workspaceName}/schemas/${schemaName}`;
      const response = await this.axios.get<ValidationSchema>(url, {
        params: {
          version_id: versionId,
        },
      });
      const headers = response.headers as AxiosHeaders;
      const schema = response.data;
      let isLatest = null;
      const headerValue = headers.get("is-latest");
      if (headerValue === "true") {
        isLatest = true;
      } else if (headerValue === "false") {
        isLatest = false;
      }

      const SchemaMetadata: FileMetadata = {
        schemaName,
        etag: headers.get("etag") as string,
        version_id: headers.get("version-id") as string,
        version_tag: headers.get("version-tag") as string,
        is_latest: isLatest,
        last_modified: new Date((headers.get("last-modified") as string) || ""),
      };

      return [schema, SchemaMetadata];
    } catch (error) {
      let errorMessage = error.message;
      if (error.response.data.detail) {
        errorMessage = error.response.data.detail;
      } else if (error.response.data.message) {
        errorMessage = error.response.data.message;
      } else if (error.response.data) {
        errorMessage = error.response.data;
      } else if (error.response) {
        errorMessage = error.response;
      }

      throw {
        response: FILES_API_ERRORS.ERROR_FETCHING_SCHEMA_FILE,
        message: errorMessage,
      };
    }
  }
}
