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
      const response = await this.axios.get(`/v1/documents/by-pmid/${pmid}`, {
        responseType: 'arraybuffer',
      });
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      const dataUint8Array = new Uint8Array(response.data);

      return new Document(documentId, dataUint8Array, documentFileName, pmid);
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }

  async getDocumentById(id: string): Promise<Document> {
    try {
      const response = await this.axios.get(`/v1/documents/by-id/${id}`, {
        responseType: 'arraybuffer',
      });
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      const dataUint8Array = new Uint8Array(response.data);

      return new Document(documentId, dataUint8Array, documentFileName, null);   
    } catch (error) {
      throw {
        response: DOCUMENT_API_ERRORS.ERROR_FETCHING_DOCUMENT,
      }
    }
  }
}
