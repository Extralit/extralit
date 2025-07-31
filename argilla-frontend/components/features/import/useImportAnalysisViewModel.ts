import { ref, watch } from 'vue';
import { useResolve } from "ts-injecty";
import { GetImportAnalysisUseCase } from '~/v1/domain/usecases/get-import-analysis-use-case';
import type {
  ImportAnalysisResponse,
  ImportStatus,
  DataframeData
} from '~/v1/domain/entities/import/ImportAnalysis';
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";

export function useImportAnalysisViewModel(props: any) {
  const isAnalyzing = ref(false);
  const hasError = ref(false);
  const errorMessage = ref('');
  const analysisResult = ref<ImportAnalysisResponse | null>(null);
  const documentActions = ref<Record<string, ImportStatus>>({});

  const importAnalysisUseCase = useResolve(GetImportAnalysisUseCase);

  const reset = () => {
    isAnalyzing.value = false;
    hasError.value = false;
    errorMessage.value = '';
    analysisResult.value = null;
    documentActions.value = {};
  };

  const analyzeImport = async (
    workspace: Workspace,
    dataframeData: DataframeData,
    matchedFiles: any[]
  ) => {
    if (!workspace || !dataframeData || dataframeData.data.length === 0) {
      return;
    }

    isAnalyzing.value = true;
    hasError.value = false;
    errorMessage.value = '';

    try {
      const result = await importAnalysisUseCase.analyzeImport(
        workspace.id,
        dataframeData,
        matchedFiles
      );

      analysisResult.value = result;
      
      // Initialize document actions from analysis result
      const actions: Record<string, ImportStatus> = {};
      Object.entries(result.documents).forEach(([reference, docInfo]) => {
        actions[reference] = docInfo.status;
      });
      documentActions.value = actions;

    } catch (error) {
      hasError.value = true;
      errorMessage.value = error.message || 'Failed to analyze import';
      console.error('Import analysis failed:', error);
    } finally {
      isAnalyzing.value = false;
    }
  };

  // Auto-trigger analysis when props change
  watch(
    () => [props.workspace, props.dataframeData, props.pdfData],
    ([workspace, dataframeData, pdfData]) => {
      if (workspace && dataframeData && pdfData?.matchedFiles) {
        analyzeImport(workspace, dataframeData, pdfData.matchedFiles);
      }
    },
    { deep: true, immediate: true }
  );

  return {
    isAnalyzing,
    hasError,
    errorMessage,
    analysisResult,
    documentActions,
    reset,
    analyzeImport
  };
}