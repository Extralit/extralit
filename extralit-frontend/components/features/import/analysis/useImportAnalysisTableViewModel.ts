import { ref, watch } from "vue";
import { useResolve } from "ts-injecty";
import { GetImportAnalysisUseCase } from "~/v1/domain/usecases/get-import-analysis-use-case";
import type { ImportAnalysisResponse, ImportStatus } from "~/v1/domain/entities/import/ImportAnalysis";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import { TableData } from "~/v1/domain/entities/table/TableData";

export function useImportAnalysisTableViewModel(props: any) {
  const isAnalyzing = ref(false);
  const hasError = ref(false);
  const errorMessage = ref("");
  const analysisResult = ref<ImportAnalysisResponse | null>(null);
  const documentActions = ref<Record<string, ImportStatus>>({});
  const lastAnalysisKey = ref<string>(""); // Track last analysis to prevent duplicates

  const importAnalysisUseCase = useResolve(GetImportAnalysisUseCase);

  const reset = () => {
    isAnalyzing.value = false;
    hasError.value = false;
    errorMessage.value = "";
    analysisResult.value = null;
    documentActions.value = {};
    lastAnalysisKey.value = "";
  };

  const analyzeImport = async (workspace: Workspace, dataframeData: TableData, matchedFiles: any[]) => {
    if (!workspace || !dataframeData || dataframeData.data.length === 0) {
      return;
    }

    // Create a unique key for this analysis to prevent duplicates
    const analysisKey = `${workspace.id}-${dataframeData.data.length}-${matchedFiles.length}`;

    // Skip if we've already analyzed this exact combination
    if (lastAnalysisKey.value === analysisKey && analysisResult.value) {
      return;
    }

    // Skip if already analyzing
    if (isAnalyzing.value) {
      return;
    }

    isAnalyzing.value = true;
    hasError.value = false;
    errorMessage.value = "";

    try {
      const result = await importAnalysisUseCase.analyzeImport(workspace.id, dataframeData, matchedFiles);

      analysisResult.value = result;
      lastAnalysisKey.value = analysisKey;

      // Initialize document actions from analysis result
      const actions: Record<string, ImportStatus> = {};
      Object.entries(result.documents).forEach(([reference, docInfo]) => {
        actions[reference] = docInfo.status;
      });
      documentActions.value = actions;
    } catch (error) {
      hasError.value = true;
      errorMessage.value = error.message || "Failed to analyze import";
    } finally {
      isAnalyzing.value = false;
    }
  };

  const retryAnalysis = () => {
    if (props.workspace && props.dataframeData && props.pdfData?.matchedFiles) {
      // Reset the last analysis key to force a retry
      lastAnalysisKey.value = "";
      analyzeImport(props.workspace, props.dataframeData, props.pdfData.matchedFiles);
    }
  };

  // Auto-trigger analysis when props change - but only when we have all required data
  watch(
    () => ({
      workspaceId: props.workspace?.id,
      dataframeLength: props.dataframeData?.data?.length,
      matchedFilesLength: props.pdfData?.matchedFiles?.length,
    }),
    (newVal, oldVal) => {
      // Only trigger if we have all required data and something actually changed
      if (newVal.workspaceId && newVal.dataframeLength > 0 && newVal.matchedFilesLength > 0) {
        // Check if this is a meaningful change
        if (
          !oldVal ||
          newVal.workspaceId !== oldVal.workspaceId ||
          newVal.dataframeLength !== oldVal.dataframeLength ||
          newVal.matchedFilesLength !== oldVal.matchedFilesLength
        ) {
          analyzeImport(props.workspace, props.dataframeData, props.pdfData.matchedFiles);
        }
      }
    },
    { immediate: true }
  );

  return {
    isAnalyzing,
    hasError,
    errorMessage,
    analysisResult,
    documentActions,
    reset,
    analyzeImport,
    retryAnalysis,
  };
}
