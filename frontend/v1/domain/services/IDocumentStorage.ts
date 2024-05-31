import { Document, Segment } from "../entities/document/Document";

export interface IDocumentStorage {
  set(document: Document): void;
  get(): Document | null;
  setSegments(segments: Segment[], reference?: string): void;
}
