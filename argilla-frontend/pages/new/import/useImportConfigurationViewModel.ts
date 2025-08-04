import { useResolve } from "ts-injecty";
import { ref, useContext, useRoute } from "@nuxtjs/composition-api";
import {
  GetImportHistoryDetailsUseCase,
  ImportHistoryDetailsResponse,
} from "~/v1/domain/usecases/get-import-history-details-use-case";
import { ImportHistoryDatasetBuilder } from "~/v1/domain/entities/import/ImportHistoryDatasetBuilder";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";
import { useRoutes } from "~/v1/infrastructure/services/useRoutes";

export const useImportConfigurationViewModel = () => {
  const { goToHome } = useRoutes();
  const route = useRoute();

  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const importHistoryData = ref<ImportHistoryDetails | null>(null);
  const datasetConfig = ref(null);
  const retryCount = ref(0);
  const maxRetries = 3;

  const getImportHistoryDetailsUseCase = useResolve(GetImportHistoryDetailsUseCase);

  const loadImportConfiguration = async (importId: string) => {
    if (!importId || importId.trim() === "") {
      error.value = "Invalid import ID provided.";
      return;
    }

    isLoading.value = true;
    error.value = null;

    try {
      // Validate import ID format (should be UUID or similar)
      if (!isValidImportId(importId)) {
        throw new Error("Invalid import ID format");
      }

      // Fetch the import history details
      const result = await getImportHistoryDetailsUseCase.execute(importId);

      if (!result.details) {
        throw new Error("No import details received");
      }

      // Convert raw data to ImportHistoryDetails instance
      const importHistoryDetails = new ImportHistoryDetails(result.details);
      importHistoryData.value = importHistoryDetails;

      // Validate that we have data to work with
      if (!result.details.data || !result.details.data.data || result.details.data.data.length === 0) {
        error.value = "This import contains no data to configure. Please try importing documents first.";
        return;
      }

      // Build dataset configuration from import history data
      const builder = new ImportHistoryDatasetBuilder(result.details);
      datasetConfig.value = builder.build();

      // Reset retry count on success
      retryCount.value = 0;
    } catch (e) {
      console.error("Failed to load import configuration:", e);

      // Handle different error types with more specific messages
      if (e.response?.status === 404) {
        error.value = "Import record not found. It may have been deleted or you don't have access to it.";
      } else if (e.response?.status === 403) {
        error.value =
          "You don't have permission to access this import record. Please check with your workspace administrator.";
      } else if (e.response?.status === 401) {
        error.value = "Your session has expired. Please sign in again.";
        // Could redirect to login here
      } else if (e.response?.status >= 500) {
        error.value = "Server error occurred while loading the import. Please try again later.";
      } else if (e.message === "Invalid import ID format") {
        error.value = "The import ID format is invalid. Please check the URL and try again.";
      } else if (e.message === "Network Error" || !navigator.onLine) {
        error.value = "Network connection error. Please check your internet connection and try again.";
      } else {
        error.value = "Failed to load import configuration. Please check your connection and try again.";
      }
    } finally {
      isLoading.value = false;
    }
  };

  const isValidImportId = (importId: string): boolean => {
    // Basic validation for import ID (UUID format or similar)
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    const numericRegex = /^\d+$/;

    return uuidRegex.test(importId) || numericRegex.test(importId) || importId.length > 0;
  };

  const retry = async () => {
    if (retryCount.value >= maxRetries) {
      error.value = `Maximum retry attempts (${maxRetries}) exceeded. Please refresh the page or contact support.`;
      return;
    }

    retryCount.value++;

    // Get import ID from route params
    const importId = route.value.params.id;
    if (importId) {
      // Add exponential backoff delay
      const delay = Math.pow(2, retryCount.value - 1) * 1000; // 1s, 2s, 4s
      await new Promise((resolve) => setTimeout(resolve, delay));

      await loadImportConfiguration(importId);
    } else {
      error.value = "Unable to determine import ID for retry.";
    }
  };

  const handleSubsetChange = (subsetName: string) => {
    if (datasetConfig.value && typeof datasetConfig.value.changeSubset === "function") {
      try {
        datasetConfig.value.changeSubset(subsetName);
      } catch (e) {
        console.error("Failed to change subset:", e);
        error.value = "Failed to change dataset subset. Please try again.";
      }
    }
  };

  const handleBreadcrumbAction = (action: string) => {
    switch (action) {
      case "home":
        goToHome();
        break;
      case "back":
        // Navigate back to previous page
        window.history.back();
        break;
      default:
        console.warn("Unknown breadcrumb action:", action);
    }
  };

  const navigateToHome = () => {
    goToHome();
  };

  const getImportId = (): string | null => {
    return route.value.params.id || null;
  };

  const resetError = () => {
    error.value = null;
  };

  return {
    isLoading,
    error,
    importHistoryData,
    datasetConfig,
    retryCount,
    maxRetries,
    loadImportConfiguration,
    retry,
    goToHome,
    navigateToHome,
    handleSubsetChange,
    handleBreadcrumbAction,
    getImportId,
    resetError,
  };
};
