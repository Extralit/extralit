import { Document } from "../entities/document/Document";

export interface IDocumentStorage {
  set(document: Document): void;
  get(): Document | null;
}
