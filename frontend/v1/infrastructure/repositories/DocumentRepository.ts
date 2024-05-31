import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Document, Segment, Segments } from "@/v1/domain/entities/document/Document";

const DOCUMENT_API_ERRORS = {
  ERROR_FETCHING_DOCUMENT: "ERROR_FETCHING_DOCUMENT",
};

export class DocumentRepository {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async getDocumentByPubmedID(pmid: string): Promise<Document>  {
    try {
      const { data } = await this.axios.get<Document>(`/v1/documents/by-pmid/${pmid}`);
      return data;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }

  async getDocumentById(id: string): Promise<Document> {
    try {
      const { data } = await this.axios.get<Document>(`/v1/documents/by-id/${id}`);
      return data;   
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }

  async getDocumentSegments(workspace: string, reference: string): Promise<Segment[]> {
    try {
      const { data } = await this.axios.get<Segments>('/v1/models/segments/', {
        params: {
          workspace,
          reference
        }
      });

      return data.items;
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }
}
