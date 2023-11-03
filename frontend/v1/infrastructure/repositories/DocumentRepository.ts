import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Document } from "@/v1/domain/entities/document/Document";

export class DocumentRepository {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async getByPubmedID(pmid: string): Promise<Document>  {
    try {
      const response = await this.axios.get(`/v1/documents/by-pmid/${pmid}`);
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      return new Document(documentId, response.data, documentFileName, pmid); 
    } catch (error) {
      throw new Error('Error fetching document');
    }
  }

  async getDocumentById(id: string): Promise<Document> {
    try {
      const response = await this.axios.get(`/v1/documents/by-id/${id}`);
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      return new Document(documentId, response.data, documentFileName, null);   
    } catch (error) {
      throw new Error('Error fetching document');
    }
  }
}
