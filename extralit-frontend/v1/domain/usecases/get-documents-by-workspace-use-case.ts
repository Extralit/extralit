import { Document } from "../entities/document/Document";
import { DocumentRepository } from "@/v1/infrastructure/repositories/DocumentRepository";

export class GetDocumentsByWorkspaceUseCase {
  constructor(private readonly documentRepository: DocumentRepository) {}

  async execute(workspaceId: string): Promise<Document[]> {
    return await this.documentRepository.getDocumentsByWorkspace(workspaceId);
  }
}
