import { ref, watch, computed } from "vue-demi";
import { useResolve } from "ts-injecty";
import { GetDocumentByIdUseCase } from "@/v1/domain/usecases/get-document-by-id-use-case";
import { useDocument } from "@/v1/infrastructure/storage/DocumentStorage";
import { Segment } from "@/v1/domain/entities/document/Document";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { waitForAsyncValue } from "@/v1/infrastructure/services/useWait";
import { useNotifications } from "~/v1/infrastructure/services/useNotifications";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";

export const useDocumentViewModel = (props: { record: any }) => {
  const notification = useNotifications();
  const getDocument = useResolve(GetDocumentByIdUseCase);
  const { state: workspaces } = useWorkspaces();
  const { state: dataset } = useDataset();
  const { state: document, set: setDocument, clear: clearDocument } = useDocument();
  const isLoading = ref(false);

  const hasDocumentLoaded = computed(() => {
    return document.id !== null;
  });

  const shouldShowDocumentPanel = computed(() => {
    return hasDocumentLoaded.value && document.url !== null;
  });

  const fetchDocument = async (metadata: any) => {
    try {
      await waitForAsyncValue(() => workspaces.selectedWorkspace?.id);

      const params: {
        workspace_id: string;
        doc_id?: string;
        pmid?: string;
        doi?: string;
        reference?: string;
      } = { workspace_id: workspaces.selectedWorkspace!.id };

      if (metadata?.reference) params.reference = metadata.reference;
      if (metadata?.doc_id) params.doc_id = metadata.doc_id;
      if (metadata?.pmid) params.pmid = metadata.pmid;
      if (metadata?.doi) params.doi = metadata.doi;

      // Ensure at least one identifier is provided
      if (Object.keys(params).length === 0) {
        throw new Error("No valid document identifier found in metadata");
      }

      await getDocument.setDocument(params);
    } catch (e) {
      const identifier = metadata?.pmid || metadata?.doi || metadata?.doc_id || metadata?.reference || "unknown";
      console.error(`Error fetching document with identifier "${identifier}":`, e);
      notification.notify({
        message: `Error fetching document with identifier "${identifier}"`,
        type: "danger",
      });
      clearDocument();
    }
  };

  const updateDocument = async (metadata: any) => {
    if (metadata?.pmid != null && document.pmid !== metadata.pmid) {
      fetchDocument(metadata);
    } else if (metadata?.doi != null && document.doi !== metadata.doi) {
      fetchDocument(metadata);
    } else if (metadata?.doc_id != null && document.id !== metadata.doc_id) {
      fetchDocument(metadata);
    } else if (!metadata?.pmid && !metadata?.doi && !metadata?.doc_id && hasDocumentLoaded.value) {
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
        message: "Error fetching document segments",
        type: "danger",
      });
    }
  };

  watch(
    () => props.record?.metadata,
    (newMetadata, oldMetadata) => {
      if (newMetadata !== oldMetadata || !document) {
        isLoading.value = true;

        try {
          updateDocument(newMetadata);
        } catch (error) {
          console.log(error);
        } finally {
          isLoading.value = false;
        }
      }
      if (newMetadata?.reference && oldMetadata?.reference !== newMetadata.reference) {
        fetchDocumentSegments(newMetadata.reference);
      }
    },
    { immediate: true }
  );

  return {
    document,
    fetchDocumentSegments,
    focusDocumentPageNumber,
    clearDocument,
    shouldShowDocumentPanel,
  };
};

export default useDocumentViewModel;
