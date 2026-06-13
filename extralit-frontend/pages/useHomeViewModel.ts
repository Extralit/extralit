import { useResolve } from "ts-injecty";
import { ref, computed, watch, onMounted } from "vue";
import { useRoutes, useFocusTab } from "~/v1/infrastructure/services";
import { GetHfDatasetCreationUseCase } from "~/v1/domain/usecases/get-hf-dataset-creation-use-case";
import { GetDatasetsUseCase } from "@/v1/domain/usecases/get-datasets-use-case";
import { GetWorkspacesUseCase } from "~/v1/domain/usecases/get-workspaces-use-case";
import { useDatasets } from "~/v1/infrastructure/storage/DatasetsStorage";
import { useWorkspaces } from "~/v1/infrastructure/storage/WorkspaceStorage";
import { useRole } from "~/v1/infrastructure/services/useRole";
import { type ImportHistoryListItem } from "~/v1/domain/usecases/get-import-history-use-case";
import { Workspace } from "~/v1/domain/entities/workspace/Workspace";
import { type BreadcrumbItem } from "~/v1/infrastructure/types/breadcrumb";

export const useHomeViewModel = () => {
  const getWorkspacesUseCase = useResolve(GetWorkspacesUseCase);
  const { isAdminOrOwnerRole } = useRole();
  const isLoadingDatasets = ref(false);
  const { goToImportDatasetFromHub, goToImportConfiguration } = useRoutes();
  const { state: datasets } = useDatasets();
  const { get: getWorkspaces, saveWorkspaces, saveSelectedWorkspace } = useWorkspaces();
  const getDatasetsUseCase = useResolve(GetDatasetsUseCase);
  const getDatasetCreationUseCase = useResolve(GetHfDatasetCreationUseCase);
  const error = ref("");
  const showImportFlow = ref(false);

  // URL parameter handling
  const route = useRoute();
  const router = useRouter();

  // Computed properties for workspace state
  const workspaces = computed(() => getWorkspaces().workspaces);
  const selectedWorkspace = computed(() => getWorkspaces().selectedWorkspace);

  // Restore workspace selection from URL parameters
  const restoreWorkspaceFromUrl = () => {
    const workspaceParam = route.query.workspace as string;
    if (workspaceParam && workspaces.value.length > 0) {
      // Find workspace by name (as used in breadcrumb links)
      const workspace = workspaces.value.find((w) => w.name === workspaceParam);
      if (workspace && workspace.id !== selectedWorkspace.value?.id) {
        saveSelectedWorkspace(workspace);
      }
    }
  };

  // Update URL parameters when workspace selection changes
  const updateUrlForWorkspace = (workspace: Workspace | null) => {
    const currentQuery = { ...route.query };

    if (workspace) {
      currentQuery.workspace = workspace.name;
    } else {
      delete currentQuery.workspace;
    }

    // Only update URL if the query actually changed
    const currentWorkspaceParam = route.query.workspace as string;
    const newWorkspaceParam = workspace?.name;

    if (currentWorkspaceParam !== newWorkspaceParam) {
      router.replace({
        path: route.path,
        query: currentQuery,
      });
    }
  };

  useFocusTab(async () => {
    await onLoadDatasets();
  });

  onMounted(async () => {
    loadDatasets();
    const workspaces = await getWorkspacesUseCase.execute();
    saveWorkspaces(workspaces);

    // Restore workspace selection from URL after workspaces are loaded
    restoreWorkspaceFromUrl();
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

  // Watch for workspace changes to update URL
  watch(
    () => selectedWorkspace.value,
    (newWorkspace) => {
      updateUrlForWorkspace(newWorkspace);
    }
  );

  // Watch for URL changes (browser back/forward navigation)
  watch(
    () => route.query.workspace,
    () => {
      restoreWorkspaceFromUrl();
    }
  );

  // Dynamic breadcrumb generation based on workspace state
  const breadcrumbs = computed((): BreadcrumbItem[] => {
    const baseBreadcrumbs: BreadcrumbItem[] = [
      { action: "clearFilters", name: "Home" }, // Will be translated in template
    ];

    if (selectedWorkspace.value) {
      baseBreadcrumbs.push({
        name: selectedWorkspace.value.name,
        link: { path: "/", query: { workspace: selectedWorkspace.value.name } },
        isWorkspace: true,
        workspaceId: selectedWorkspace.value.id,
      });
    }

    return baseBreadcrumbs;
  });

  const openImportFlow = () => {
    showImportFlow.value = !showImportFlow.value;
  };

  const isImportFlowVisible = computed(() => {
    return showImportFlow.value;
  });

  // Workspace selection methods using global store
  const setSelectedWorkspace = (workspace: Workspace | null) => {
    saveSelectedWorkspace(workspace);
    // URL will be updated automatically via the watcher
  };

  const setSelectedWorkspaceId = (workspaceId: string | null) => {
    if (workspaceId === null) {
      saveSelectedWorkspace(null);
    } else {
      const workspace = workspaces.value.find((w) => w.id === workspaceId);
      saveSelectedWorkspace(workspace || null);
    }
    // URL will be updated automatically via the watcher
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

  const handleImportCompleted = async (recentImportsRef?: any) => {
    // Refresh datasets and workspaces after import completion
    await onLoadDatasets();

    // Refresh recent imports list if ref is provided
    if (recentImportsRef?.refresh) {
      await recentImportsRef.refresh();
    }

    // Close the import modal
    showImportFlow.value = false;
  };

  return {
    datasets,
    workspaces,
    selectedWorkspace,
    breadcrumbs,
    isLoadingDatasets,
    getNewHfDatasetByRepoId,
    goToImportConfiguration,
    isAdminOrOwnerRole,
    exampleDatasets,
    error,
    showImportFlow,
    isImportFlowVisible,
    openImportFlow,
    setSelectedWorkspace,
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
