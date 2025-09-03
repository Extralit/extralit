/**
 * View model for DocumentsList component
 * Handles document loading and grouping logic
 */

import { ref, computed, watch, onMounted } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { GetDocumentsByWorkspaceUseCase } from "~/v1/domain/usecases/get-documents-by-workspace-use-case";
import { Document } from "~/v1/domain/entities/document/Document";

export interface DocumentGroup {
  reference: string | null;
  documents: Document[];
  metadata: Record<string, any> | null;
}

export const useDocumentsListViewModel = (props: { workspaceId: string }) => {
  const getDocumentsByWorkspaceUseCase = useResolve(GetDocumentsByWorkspaceUseCase);

  // Reactive state
  const documents = ref<Document[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // Modal state
  const showMetadataModal = ref(false);
  const selectedDocumentMetadata = ref(null as any);
  const selectedDocumentName = ref("" as string);

  // Computed properties
  const groupedDocuments = computed(() => {
    return groupDocumentsByReference(documents.value);
  });

  const totalFiles = computed(() => {
    return documents.value.length;
  });

  const stats = computed(() => {
    const grouped = groupDocumentsByReference(documents.value);
    return {
      totalReferences: grouped.length,
      totalFiles: documents.value.length,
    };
  });

  // Document loading
  const loadDocuments = async () => {
    if (!props.workspaceId) {
      documents.value = [];
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      const response = await getDocumentsByWorkspaceUseCase.execute(props.workspaceId);
      documents.value = response;
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Failed to load documents:", err);
      error.value = "Failed to load documents. Please try again.";
      documents.value = [];
    } finally {
      isLoading.value = false;
    }
  };

  // Document grouping logic
  const groupDocumentsByReference = (docs: Document[]): DocumentGroup[] => {
    const groups = new Map<string, DocumentGroup>();

    docs.forEach((document) => {
      const key = document.reference || "no-reference";

      if (!groups.has(key)) {
        groups.set(key, {
          reference: document.reference,
          documents: [],
          metadata: document.metadata,
        });
      }

      groups.get(key)!.documents.push(document);
    });

    return Array.from(groups.values()).sort((a, b) => {
      // Sort by reference, with 'no-reference' at the end
      if (!a.reference && b.reference) return 1;
      if (a.reference && !b.reference) return -1;
      if (!a.reference && !b.reference) return 0;
      return a.reference.localeCompare(b.reference);
    });
  };

  // Document actions
  const openDocument = (document: Document) => {
    if (document.url) {
      window.open(document.url, "_blank");
    }
  };

  // Thumbnail error handling
  const onThumbnailError = (event: Event) => {
    const target = event.target as HTMLImageElement;
    if (target) {
      // Hide the broken image and show placeholder
      target.style.display = 'none';
      const thumbnailContainer = target.parentElement;
      if (thumbnailContainer) {
        thumbnailContainer.innerHTML = '<div class="thumbnail-placeholder"><svg-icon name="document" width="24" height="24" /></div>';
      }
    }
  };

  // Modal methods
  const showDocumentMetadata = (document: Document) => {
    selectedDocumentMetadata.value = document.metadata;
    selectedDocumentName.value = document.file_name || "Unknown Document";
    showMetadataModal.value = true;
  };

  const closeMetadataModal = () => {
    showMetadataModal.value = false;
    selectedDocumentMetadata.value = null;
    selectedDocumentName.value = "";
  };

  // Watch for workspace changes and reload data
  watch(
    () => props.workspaceId,
    async (newWorkspaceId, oldWorkspaceId) => {
      // Load data when workspace changes, including from null to a value
      if (newWorkspaceId && newWorkspaceId !== oldWorkspaceId) {
        await loadDocuments();
      }
    },
    { immediate: false }
  );

  // Load data on component mount only if workspace is available
  onMounted(async () => {
    if (props.workspaceId) {
      await loadDocuments();
    }
  });

  // Retry mechanism for error recovery
  const retryLoad = async () => {
    await loadDocuments();
  };

  // Public method to refresh the documents list
  const refresh = async () => {
    await loadDocuments();
  };

  return {
    // Reactive state
    documents,
    isLoading,
    error,

    // Modal state
    showMetadataModal,
    selectedDocumentMetadata,
    selectedDocumentName,

    // Computed properties
    groupedDocuments,
    totalFiles,
    stats,

    // Methods
    loadDocuments,
    openDocument,
    onThumbnailError,
    retryLoad,
    refresh,
    showDocumentMetadata,
    closeMetadataModal,
  };
};
