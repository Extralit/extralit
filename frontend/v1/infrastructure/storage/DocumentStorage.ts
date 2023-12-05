import { Document } from "@/v1/domain/entities/document/Document";
import { IDocumentStorage } from "@/v1/domain/services/IDocumentStorage";
import { useStoreFor } from "@/v1/store/create";


const useStoreForDocument = useStoreFor<Document, IDocumentStorage>(Document);

export const useDocument = () => {
  const state = useStoreForDocument();

  const set = (document: Document): void => {
    state.save(document)
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
    clear
  };
};

