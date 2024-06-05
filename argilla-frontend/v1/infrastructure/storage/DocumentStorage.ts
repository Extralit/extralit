import { Document, Segment } from "@/v1/domain/entities/document/Document";
import { IDocumentStorage } from "@/v1/domain/services/IDocumentStorage";
import { useStoreFor } from "@/v1/store/create";


const useStoreForDocument = useStoreFor<Document, IDocumentStorage>(Document);

export const useDocument = () => {
  const state = useStoreForDocument();

  const set = (document: Document): void => {
    const currentDocument = get();
    if (currentDocument && !currentDocument.id) {
      if (currentDocument.segments && !document.segments) {
        document.segments = currentDocument.segments;
      }
      if (currentDocument.reference && !document.reference) {
        document.reference = currentDocument.reference;
      }
    }
    state.save(document);
  }

  const setSegments = (segments: Segment[], reference?: string): void => {
    const document = get();
    if (document) {
      document.segments = segments;
      document.reference = reference;
      set(document);
    }
  }

  const get = (): Document | null => {
    return state.get();
  }

  const clear = (): void => {
    state.save(new Document(null, null, null, null));
  }

  return {
    ...state,
    set,
    get,
    clear,
    setSegments,
  };
};

