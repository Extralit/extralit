import { Segment } from "../entities/document/Document";
import { IDocumentStorage } from "../services/IDocumentStorage";
import { DocumentRepository } from "@/v1/infrastructure/repositories/DocumentRepository";

export class GetDocumentByRecordMetadataUseCase {
  constructor(
    private readonly documentRepository: DocumentRepository,
    private readonly documentStorage: IDocumentStorage
  ) { }

  createParams(
    metadata: Record<string, any> | null,
    workspaceId: string
  ): {
    workspace_id: string;
    doc_id?: string;
    pmid?: string;
    doi?: string;
    reference?: string;
  } {
    const params: {
      workspace_id: string;
      doc_id?: string;
      pmid?: string;
      doi?: string;
      reference?: string;
    } = { workspace_id: workspaceId };

    if (metadata?.reference) params.reference = metadata.reference;
    if (metadata?.doc_id) params.doc_id = metadata.doc_id;

    return params;
  }

  async setDocument(params: {
    workspace_id: string;
    doc_id?: string;
    pmid?: string;
    doi?: string;
    reference?: string;
  }) {
    const documents = await this.documentRepository.getDocuments(params);

    if (documents.length === 0) {
      return null;
    }

    // For now, we'll use the first document found
    // In the future, you might want to add logic to handle multiple documents
    if (documents.length > 1) {
      console.warn(`Multiple documents found (${documents.length}). Using the first one.`);
    }

    this.documentStorage.set(documents[0]);
  }

  async setSegments(workspace: string, reference: string): Promise<Segment[]> {
    const segments = await this.documentRepository.getDocumentSegments(workspace, reference);
    this.documentStorage.setSegments(segments, reference);
    return segments;
  }

  get() {
    return this.documentStorage.get();
  }
}
