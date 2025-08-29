import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Document, Segment, Segments } from "@/v1/domain/entities/document/Document";

const DOCUMENT_API_ERRORS = {
  ERROR_FETCHING_DOCUMENT: "ERROR_FETCHING_DOCUMENT",
  ERROR_LISTING_DOCUMENTS: "ERROR_LISTING_DOCUMENTS",
  ERROR_FETCHING_SEGMENTS: "ERROR_FETCHING_SEGMENTS",
};

export class DocumentRepository {
  constructor(private readonly axios: NuxtAxiosInstance) { }

  async getDocuments(params: {
    workspace_id: string;
    doc_id?: string;
    pmid?: string;
    doi?: string;
    reference?: string;
  }): Promise<Document[]> {
    try {
      const queryParams = Object.fromEntries(Object.entries(params).filter(([_, value]) => value !== undefined));

      if (Object.keys(queryParams).length === 0) {
        throw new Error("At least one identifier parameter must be provided");
      }

      const { data } = await this.axios.get<Document[]>("/v1/documents", {
        params: queryParams,
      });
      return data;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      };
    }
  }

  async getDocumentSegments(workspace: string, reference: string): Promise<Segment[]> {
    try {
      const { data } = await this.axios.get<Segments>("/v1/models/segments/", {
        params: { workspace, reference },
      });

      return data.items;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_SEGMENTS,
      };
    }
  }

  async getDocumentsByWorkspace(workspaceId: string): Promise<Document[]> {
    try {
      const { data } = await this.axios.get<Document[]>(`/v1/documents/workspace/${workspaceId}`);
      return data;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_LISTING_DOCUMENTS,
      };
    }
  }
}
