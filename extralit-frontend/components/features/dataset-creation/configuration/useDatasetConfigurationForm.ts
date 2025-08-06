import { useResolve } from "ts-injecty";
import { ref } from "vue-demi";
import { availableFieldTypes } from "~/v1/domain/entities/hub/FieldCreation";
import { availableQuestionTypes } from "~/v1/domain/entities/hub/QuestionCreation";
import { CreateDatasetUseCase } from "~/v1/domain/usecases/create-dataset-use-case";
import { useRoutes } from "~/v1/infrastructure/services";
import { DatasetCreation } from "~/v1/domain/entities/hub/DatasetCreation";
import { ImportHistoryDetails } from "~/v1/domain/entities/import/ImportHistoryDetails";

export const useDatasetConfigurationForm = () => {
  const isLoading = ref(false);
  const { goToFeedbackTaskAnnotationPage } = useRoutes();
  const createDatasetUseCase = useResolve(CreateDatasetUseCase);

  const create = async (dataset: DatasetCreation, importData?: ImportHistoryDetails) => {
    isLoading.value = true;

    try {
      // If this is an ImportHistory-based dataset, ensure proper metadata handling
      if (importData) {
        // Validate that the dataset has proper reference field mapping
        const mappings = dataset.mappings;
        const hasReferenceMapping = mappings.metadata.some((m) => m.target === "reference");

        if (!hasReferenceMapping && importData.fieldNames.includes("reference")) {
          console.warn(
            "ImportHistory dataset missing reference field mapping - this may affect record.metadata.reference population"
          );
        }
      }

      const datasetId = await createDatasetUseCase.execute(dataset);

      if (!datasetId) return;

      goToFeedbackTaskAnnotationPage(datasetId);
    } finally {
      isLoading.value = false;
    }
  };

  return {
    availableFieldTypes,
    availableQuestionTypes,
    create,
    isLoading,
  };
};
