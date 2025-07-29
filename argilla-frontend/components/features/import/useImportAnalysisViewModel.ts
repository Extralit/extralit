import { ref, computed, watch, useContext } from '@nuxtjs/composition-api';
import type {
  ImportAnalysisResponse,
  ImportStatus,
  DataframeData,
  DocumentImportAnalysis,
} from '~/v1/domain/entities/import/ImportAnalysis';
import { Workspace } from '~/v1/domain/entities/workspace/Workspace';
import { ImportAnalysisUseCase } from '~/v1/domain/usecases/import-analysis-use-case';

export function useImportAnalysisViewModel(props: {
  analysisData: ImportAnalysisResponse;
  dataframeData: DataframeData | null;
  workspace: Workspace;
  loading: boolean;
}) {
  // Access Nuxt axios instance
  const { $axios } = useContext();

  // Create use case instance
  const importAnalysisUseCase = new ImportAnalysisUseCase($axios);

  // Reactive state
  const isAnalyzing = ref(false);
  const hasError = ref(false);
  const errorMessage = ref('');
  const analysisResult = ref<ImportAnalysisResponse | null>(null);
  const documentActions = ref<Record<string, ImportStatus>>({});
  const originalStatuses = ref<Record<string, ImportStatus>>({});

  const workspaceId = computed(() => props.workspace.id);

  const shouldAnalyze = computed(() => {
    return props.dataframeData &&
           props.dataframeData.data.length > 0 &&
           !analysisResult.value &&
           !isAnalyzing.value &&
           workspaceId.value;
  });

  // Methods
  const performAnalysis = async (pdfFiles?: File[]) => {
    if (!props.dataframeData || !workspaceId.value) {
      showError('No data available for analysis or missing workspace ID');
      return null;
    }

    isAnalyzing.value = true;
    hasError.value = false;
    errorMessage.value = '';

    try {
      const result = await importAnalysisUseCase.analyzeImport(
        workspaceId.value,
        props.dataframeData,
        pdfFiles
      );

      analysisResult.value = result;

      // Reset document actions for new analysis
      documentActions.value = {};
      originalStatuses.value = {};

      // Store original statuses
      Object.entries(result.documents || {}).forEach(([reference, docInfo]: [string, DocumentImportAnalysis]) => {
        originalStatuses.value[reference] = docInfo.status;
      });

      return result;

    } catch (error) {
      console.error('Analysis failed:', error);
      showError(error.message || 'Failed to analyze import data');
      return null;
    } finally {
      isAnalyzing.value = false;
    }
  };

  const showError = (message: string) => {
    hasError.value = true;
    errorMessage.value = message;
  };

  const reset = () => {
    hasError.value = false;
    errorMessage.value = '';
    analysisResult.value = null;
    documentActions.value = {};
    originalStatuses.value = {};
    isAnalyzing.value = false;
  };

  // Watch for dataframe data changes and trigger analysis
  watch(
    () => props.dataframeData,
    async (newData) => {
      if (newData && newData.data.length > 0 && workspaceId.value) {
        // Reset previous analysis
        analysisResult.value = null;
        documentActions.value = {};
        originalStatuses.value = {};

        // Perform new analysis
        await performAnalysis();
      }
    },
    { immediate: true }
  );

  // Watch for workspace changes
  watch(
    workspaceId,
    () => {
      if (shouldAnalyze.value) {
        performAnalysis();
      }
    }
  );

  return {
    // State
    importAnalysisUseCase,
    isAnalyzing,
    hasError,
    errorMessage,
    analysisResult,
    documentActions,
    originalStatuses,

    // Computed
    workspaceId,
    shouldAnalyze,

    // Methods
    performAnalysis,
    showError,
    reset,
  };
}