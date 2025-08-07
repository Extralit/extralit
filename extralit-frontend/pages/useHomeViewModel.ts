import { useResolve } from "ts-injecty";
import { ref, useFetch, computed } from "@nuxtjs/composition-api";
import { useRoutes, useFocusTab } from "~/v1/infrastructure/services";
import { GetHfDatasetCreationUseCase } from "~/v1/domain/usecases/get-hf-dataset-creation-use-case";
import { GetDatasetsUseCase } from "@/v1/domain/usecases/get-datasets-use-case";
import { GetWorkspacesUseCase } from "~/v1/domain/usecases/get-workspaces-use-case";
import { useDatasets } from "~/v1/infrastructure/storage/DatasetsStorage";
import { useRole } from "~/v1/infrastructure/services/useRole";
import { ImportHistoryListItem } from "~/v1/domain/usecases/get-import-history-use-case";

export const useHomeViewModel = () => {
  const workspaces = ref<any[]>([]);
  const getWorkspacesUseCase = useResolve(GetWorkspacesUseCase);
  const { isAdminOrOwnerRole } = useRole();
  const isLoadingDatasets = ref(false);
  const { goToImportDatasetFromHub, goToImportConfiguration } = useRoutes();
  const { state: datasets } = useDatasets();
  const getDatasetsUseCase = useResolve(GetDatasetsUseCase);
  const getDatasetCreationUseCase = useResolve(GetHfDatasetCreationUseCase);
  const error = ref("");
  const showImportModal = ref(false);

  useFocusTab(async () => {
    await onLoadDatasets();
  });

  useFetch(async () => {
    loadDatasets();
    workspaces.value = await getWorkspacesUseCase.execute();
  });

  const getNewHfDatasetByRepoId = async (repositoryId: string) => {
    try {
      await getDatasetCreationUseCase.execute(repositoryId);
      goToImportDatasetFromHub(repositoryId);
    } catch {
      error.value = "datasetCreation.cantLoadRepository";
    }
  };

  const exampleDatasets = [
    {
      repoId: "stanfordnlp/imdb",
      task: "Text Classification",
      tags: ["sentiment-classification"],
      icon: "text-classification",
      color: "hsl(25, 95%, 53%)",
      rows: "100K",
    },
    {
      repoId: "databricks/databricks-dolly-15k",
      task: "Question answering",
      tags: ["instruction-dataset", "rag"],
      icon: "question-answering",
      color: "hsl(217, 91%, 60%)",
      rows: "15K",
    },
    {
      repoId: "dvilasuero/finepersonas-v0.1-tiny-flux-schnell",
      task: "Text to Image",
      tags: ["synthetic", "rlaif"],
      icon: "text-to-image",
      color: "hsl(38, 92%, 50%)",
      rows: "350",
    },
  ];

  const onLoadDatasets = async () => {
    await getDatasetsUseCase.execute();
  };

  const loadDatasets = async () => {
    isLoadingDatasets.value = true;

    await onLoadDatasets();

    isLoadingDatasets.value = false;
  };

  const openImportModal = () => {
    showImportModal.value = !showImportModal.value;
  };

  const isImportModalVisible = computed(() => {
    return showImportModal.value;
  });

  // Workspace selection for import
  const selectedWorkspaceId = ref<string | null>(null);

  const setSelectedWorkspaceId = (workspaceId: string | null) => {
    selectedWorkspaceId.value = workspaceId;
  };

  // Import history modal state
  const showImportHistoryModal = ref(false);

  const isImportHistoryModalVisible = computed(() => {
    return showImportHistoryModal.value;
  });

  const openImportHistoryModal = () => {
    showImportHistoryModal.value = true;
  };

  const closeImportHistoryModal = () => {
    showImportHistoryModal.value = false;
  };

  // Navigation methods for import configuration routing
  const handleImportSelected = (importRecord: ImportHistoryListItem) => {
    goToImportConfiguration(importRecord.id);
  };

  const handleViewImportDetails = (importRecord: ImportHistoryListItem) => {
    closeImportHistoryModal();
    goToImportConfiguration(importRecord.id);
  };

  const handleImportCompleted = async () => {
    // Refresh datasets and workspaces after import completion
    await onLoadDatasets();
    // Close the import modal
    showImportModal.value = false;
  };

  return {
    datasets,
    workspaces,
    isLoadingDatasets,
    getNewHfDatasetByRepoId,
    goToImportConfiguration,
    isAdminOrOwnerRole,
    exampleDatasets,
    error,
    showImportModal,
    isImportModalVisible,
    openImportModal,
    selectedWorkspace: selectedWorkspaceId,
    setSelectedWorkspaceId,
    showImportHistoryModal,
    isImportHistoryModalVisible,
    openImportHistoryModal,
    closeImportHistoryModal,
    handleImportSelected,
    handleViewImportDetails,
    handleImportCompleted,
  };
};
