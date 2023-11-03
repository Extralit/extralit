import { useResolve } from "ts-injecty";
import {
  GetDocumentByIdUseCase,
} from "~/v1/domain/usecases/get-document-by-id-use-case";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";


export const useDocumentViewModel = () => {
  const getDocument = useResolve(GetDocumentByIdUseCase);
  const { state: document } = useDocument();

  const setDocument = async (id: string) => {
    await getDocument.set(id);
  };

  return {
    document,
    setDocument
  };
};

export default useDocumentViewModel;