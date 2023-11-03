import { DocumentRepository } from "@/v1/infrastructure/repositories/DocumentRepository";
import { IDocumentStorage } from "../services/IDocumentStorage";

export class GetDocumentByIdUseCase {
  constructor(
    private readonly documentRepository: DocumentRepository,
    private readonly documentStorage: IDocumentStorage
  ) {}

  async set(id: string) {
    const document = await this.documentRepository.getDocumentById(id);
    // console.log(this.documentStorage)
    this.documentStorage.set(document);
  }

  async get() {
    return this.documentStorage.get()
  }
}
