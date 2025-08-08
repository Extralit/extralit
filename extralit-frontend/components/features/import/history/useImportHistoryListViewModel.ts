/**
 * View model for ImportHistoryList component
 * Handles loading of import history
 */

import { useResolve } from "ts-injecty";
import { GetImportHistoryUseCase } from "~/v1/domain/usecases/get-import-history-use-case";

export function useImportHistoryListViewModel(props: any) {
  const getImportHistoryUseCase = useResolve(GetImportHistoryUseCase);

  return {
    // Use case reference
    getImportHistoryUseCase,
  };
}
