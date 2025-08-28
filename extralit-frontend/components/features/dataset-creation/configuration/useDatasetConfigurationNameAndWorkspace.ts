import { useFetch } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { ref } from "vue-demi";
import { GetWorkspacesUseCase } from "~/v1/domain/usecases/get-workspaces-use-case";
import { GetImportCompatibleDatasetsUseCase } from "~/v1/domain/usecases/get-import-compatible-datasets-use-case";
import { BackendDataset } from "~/v1/infrastructure/types/dataset";

export const useDatasetConfigurationNameAndWorkspace = () => {
  const workspaces = ref<any[]>([]);
  const compatibleDatasets = ref<BackendDataset[]>([]);
  const isLoadingCompatibleDatasets = ref(false);
  const workflowType = ref<"create" | "append">("create");
  const selectedTargetDataset = ref<BackendDataset | null>(null);

  const getWorkspacesUseCase = useResolve(GetWorkspacesUseCase);
  const getImportCompatibleDatasetsUseCase = useResolve(GetImportCompatibleDatasetsUseCase);

  useFetch(async () => {
    workspaces.value = await getWorkspacesUseCase.execute();
  });

  const loadCompatibleDatasets = async (columnNames: string[], workspaceId?: string) => {
    if (!columnNames.length) {
      compatibleDatasets.value = [];
      return;
    }

    try {
      isLoadingCompatibleDatasets.value = true;
      compatibleDatasets.value = await getImportCompatibleDatasetsUseCase.execute({
        columnNames,
        workspaceId,
      });
    } catch (error) {
      console.error("Error loading compatible datasets:", error);
      compatibleDatasets.value = [];
    } finally {
      isLoadingCompatibleDatasets.value = false;
    }
  };

  const onWorkflowTypeChange = async (columnNames: string[], workspaceId?: string) => {
    if (workflowType.value === "append") {
      await loadCompatibleDatasets(columnNames, workspaceId);
    } else {
      compatibleDatasets.value = [];
      selectedTargetDataset.value = null;
    }
  };

  return {
    workspaces,
    compatibleDatasets,
    isLoadingCompatibleDatasets,
    workflowType,
    selectedTargetDataset,
    loadCompatibleDatasets,
    onWorkflowTypeChange,
  };
};
