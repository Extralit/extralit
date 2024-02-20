import { useResolve } from "ts-injecty";
import {
  GetDocumentByIdUseCase,
} from "~/v1/domain/usecases/get-document-by-id-use-case";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";
import { Notification } from "@/models/Notifications";

export const useDocumentViewModel = () => {
  const getDocument = useResolve(GetDocumentByIdUseCase);
  const { state: document, set: setDocument, clear: clearDocument } = useDocument();

  const setDocumentByID = async (id: string) => {
    try {
      await getDocument.setDocumentByID(id);
    } catch (e) {
      Notification.dispatch("notify", {
        message: `Error fetching document with ID ${id}`,
        type: 'error',
      });
      setDocument({ id: null, file_data: null, file_name: null, pmid: null });
    }
  };

  const setDocumentByPubmedID = async (pmid: string) => {
    try {
      await getDocument.setDocumentByPubmedID(pmid);
    } catch (e) {
      Notification.dispatch("notify", {
        message: `Error fetching document with pmid "${pmid}"`,
        type: 'error',
      });
      setDocument({ id: null, file_data: null, file_name: null, pmid: null });
    }
  };

  const setDocumentPageNumber = (pageNumber: number | string) => {
    setDocument({ ...document, page_number: pageNumber });
  };

  return {
    document,
    setDocumentByID: setDocumentByID,
    setDocumentByPubmedID: setDocumentByPubmedID,
    clearDocument: clearDocument,
    setDocumentPageNumber: setDocumentPageNumber,
  };
};

export default useDocumentViewModel;