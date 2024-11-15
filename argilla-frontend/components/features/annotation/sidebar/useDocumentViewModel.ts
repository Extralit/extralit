import { ref, watch, computed } from 'vue-demi';
import { useResolve } from "ts-injecty";
import { GetDocumentByIdUseCase } from "@/v1/domain/usecases/get-document-by-id-use-case";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";
import { Segment } from "@/v1/domain/entities/document/Document";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { waitForAsyncValue } from "@/v1/infrastructure/services/useWait";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";

export const useDocumentViewModel = (
  props: {
    record: any;
  },
) => {
  const notification = useNotifications();
  const getDocument = useResolve(GetDocumentByIdUseCase);
  const { state: dataset } = useDataset();
  const { state: document, set: setDocument, clear: clearDocument } = useDocument();
  const isLoading = ref(false);

  const hasDocumentLoaded = computed(() => {
    return document.id !== null;
  });
  const hasDocument = computed(() => {
    return props.record.metadata === null || props.record.metadata?.doc_id != null || props.record.metadata?.pmid != null;
  })

  const fetchDocumentByID = async (id: string) => {
    try {
      await getDocument.setDocumentByID(id);
    } catch (e) {
      notification.notify({
        message: `Error fetching document with ID ${id}`,
        type: 'danger',
      });
      clearDocument();
    }
  };

  const fetchDocumentByPubmedID = async (pmid: string) => {
    try {
      await getDocument.setDocumentByPubmedID(pmid);
    } catch (e) {
      notification.notify({
        message: `Error fetching document with pmid "${pmid}"`,
        type: 'danger',
      });
      clearDocument();
    }
  };

  const updateDocument = async (metadata: any) => {
    if (metadata?.pmid != null) {
      if (document.pmid !== metadata.pmid) {
        fetchDocumentByPubmedID(metadata.pmid);
      }
    } else if (metadata?.doc_id != null && document.id !== metadata.doc_id) {
      fetchDocumentByID(metadata.doc_id);
    } else if (!metadata?.pmid && !metadata?.doc_id && hasDocumentLoaded.value) {
      clearDocument();
    }

    if (metadata?.page_number != null) {
      focusDocumentPageNumber(metadata.page_number);
    }
  };

  const focusDocumentPageNumber = (pageNumber: number | string) => {
    // @ts-ignore
    setDocument({ ...document, page_number: pageNumber });
  };

  const fetchDocumentSegments = async (reference: string): Promise<Segment[]> => {
    try {
      await waitForAsyncValue(() => dataset.workspaceName);
      const segments = await getDocument.setSegments(dataset.workspaceName, reference);
      return segments;
    } catch (e) {
      notification.notify({
        message: `Error fetching document segments`,
        type: 'danger',
      });
    }
  };

  watch(
    () => props.record?.metadata,
    (newMetadata, oldMetadata) => {
      if ((newMetadata !== oldMetadata || !document)) {
        isLoading.value = true;

        try {
          updateDocument(newMetadata);
        } catch (error) {
          console.log(error)
        } finally {
          isLoading.value = false;
          if (!hasDocumentLoaded.value) {
            // TODO closePanel();
          }
        }
      }
      if (newMetadata?.reference && oldMetadata?.reference !== newMetadata.reference) {
        fetchDocumentSegments(newMetadata.reference);
      }
    },
    { immediate: true },
  );

  return {
    document,
    fetchDocumentByID,
    fetchDocumentByPubmedID,
    fetchDocumentSegments,
    focusDocumentPageNumber,
    clearDocument,
  };
};

export default useDocumentViewModel;