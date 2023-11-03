import { type NuxtAxiosInstance } from "@nuxtjs/axios";
import { Document } from "@/v1/domain/entities/document/Document";

export class DocumentRepository {
  constructor(
    private readonly axios: NuxtAxiosInstance,
  ) {}

  async getByPubmedID(pmid: string): Promise<Document>  {
    try {
      const response = await this.axios.get(`/v1/documents/by-pmid/${pmid}`, {
        responseType: 'arraybuffer',
      });
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      // const dataBlob = new Blob([response.data], { type: 'application/pdf' });
      const dataUint8Array = new Uint8Array(response.data);

      return new Document(documentId, dataUint8Array, documentFileName, pmid); 
    } catch (error) {
      throw new Error('Error fetching document');
    }
  }

  async getDocumentById(id: string): Promise<Document> {
    try {
      const response = await this.axios.get(`/v1/documents/by-id/${id}`, {
        responseType: 'arraybuffer',
      });
      console.log(response.headers)
      const documentId = response.headers['x-document-id'];
      const documentFileName = response.headers['x-document-file-name'];

      const dataUint8Array = new Uint8Array(response.data);

      return new Document(documentId, dataUint8Array, documentFileName, null);   
    } catch (error) {
      throw new Error('Error fetching document');
    }
  }
}
