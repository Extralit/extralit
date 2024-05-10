import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Document } from "@/v1/domain/entities/document/Document";

const DOCUMENT_API_ERRORS = {
  ERROR_FETCHING_DOCUMENT: "ERROR_FETCHING_DOCUMENT",
};

export class DocumentRepository {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async getDocumentByPubmedID(pmid: string): Promise<Document>  {
    try {
      const response = await this.axios.get(`/v1/documents/by-pmid/${pmid}`);
      const url = response.data.url

      console.log(await this.axios.get(`/v1/models/schemas/itn-recalibration`))

      return new Document(
        response.data.id, 
        url, 
        response.data.file_name, 
        response.data.pmid);

    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }

  async getDocumentById(id: string): Promise<Document> {
    try {
      const response = await this.axios.get(`/v1/documents/by-id/${id}`);
      const url = response.data.url

      return new Document(
        response.data.id, 
        url, 
        response.data.file_name, 
        response.data.pmid);   

    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }
}
