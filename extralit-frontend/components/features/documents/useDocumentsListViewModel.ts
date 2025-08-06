/**
 * View model for DocumentsList component
 * Handles document loading and grouping logic
 */

import { useResolve } from "ts-injecty";
import { GetDocumentsByWorkspaceUseCase } from "~/v1/domain/usecases/get-documents-by-workspace-use-case";
import { Document } from "~/v1/domain/entities/document/Document";

export interface DocumentGroup {
  reference: string | null;
  documents: Document[];
  metadata: Record<string, any> | null;
}

export function useDocumentsListViewModel() {
  const getDocumentsByWorkspaceUseCase = useResolve(GetDocumentsByWorkspaceUseCase);

  return {
    // Use cases
    getDocumentsByWorkspaceUseCase,

    // Document loading
    async loadDocuments(workspaceId: string): Promise<Document[]> {
      return await getDocumentsByWorkspaceUseCase.execute(workspaceId);
    },

    // Document grouping logic
    groupDocumentsByReference(documents: Document[]): DocumentGroup[] {
      const groups = new Map<string, DocumentGroup>();

      documents.forEach((document) => {
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
    },

    // Statistics calculation
    calculateStats(documents: Document[]) {
      const groupedDocuments = this.groupDocumentsByReference(documents);
      return {
        totalReferences: groupedDocuments.length,
        totalFiles: documents.length,
      };
    },

    // Document actions
    openDocument(document: Document) {
      if (document.url) {
        window.open(document.url, "_blank");
      }
    },
  };
}

// Backward compatibility export
export const getDocumentsByWorkspace = async (workspaceId: string): Promise<Document[]> => {
  const viewModel = useDocumentsListViewModel();
  return await viewModel.loadDocuments(workspaceId);
};
