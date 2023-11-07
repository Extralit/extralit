import { useResolve } from "ts-injecty";
import {
  GetDocumentByIdUseCase,
} from "~/v1/domain/usecases/get-document-by-id-use-case";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";


export const useDocumentViewModel = () => {
  const getDocument = useResolve(GetDocumentByIdUseCase);
  const { state: document } = useDocument();

  const setDocumentByID = async (id: string) => {
    await getDocument.setDocumentByID(id);
  };

  const setDocumentByPubmedID = async (pmoid: string) => {
    await getDocument.setDocumentByPubmedID(pmoid);
  };

  return {
    document,
    setDocumentByID: setDocumentByID,
    setDocumentByPubmedID: setDocumentByPubmedID
  };
};

export default useDocumentViewModel;