import { DocumentRepository } from "@/v1/infrastructure/repositories/DocumentRepository";
import { IDocumentStorage } from "../services/IDocumentStorage";

export class GetDocumentByIdUseCase {
  constructor(
    private readonly documentRepository: DocumentRepository,
    private readonly documentStorage: IDocumentStorage
  ) {}

  async setDocumentByID(id: string) {
    const document = await this.documentRepository.getDocumentById(id);

    this.documentStorage.set(document);
  }

  async setDocumentByPubmedID(id: string) {
    const document = await this.documentRepository.getDocumentByPubmedID(id);

    this.documentStorage.set(document);
  }

  async get() {
    return this.documentStorage.get()
  }
}
