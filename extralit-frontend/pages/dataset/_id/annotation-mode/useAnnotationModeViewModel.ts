import { computed, onBeforeMount, ref, useRouter, watch } from "@nuxtjs/composition-api";
import { useResolve } from "ts-injecty";
import { useDatasetViewModel } from "../useDatasetViewModel";
import { GetDatasetByIdUseCase } from "@/v1/domain/usecases/get-dataset-by-id-use-case";
import { useDataset } from "@/v1/infrastructure/storage/DatasetStorage";
import { useWorkspaces } from "@/v1/infrastructure/storage/WorkspaceStorage";
import { RecordCriteria } from "~/v1/domain/entities/record/RecordCriteria";
import { useRoutes, useUser, useRole } from "~/v1/infrastructure/services";
import { RecordStatus } from "~/v1/domain/entities/record/RecordAnswer";

export const useAnnotationModeViewModel = () => {
  const { isAdminOrOwner } = useRole();
  const router = useRouter();
  const routes = useRoutes();
  const { user } = useUser();
  const { state: dataset } = useDataset();
  const workspaceStore = useWorkspaces();
  const getDatasetUseCase = useResolve(GetDatasetByIdUseCase);

  const { datasetId, isLoadingDataset, handleError, createRootBreadCrumbs } = useDatasetViewModel();

  const breadcrumbs = computed(() => createRootBreadCrumbs(dataset));

  const recordCriteria = ref<RecordCriteria>(
    new RecordCriteria(
      datasetId,
      routes.getQueryParams<string>("page"),
      routes.getQueryParams<RecordStatus>("status"),
      routes.getQueryParams<string>("search"),
      routes.getQueryParams<string>("metadata"),
      routes.getQueryParams<string>("sort"),
      routes.getQueryParams<string>("response"),
      routes.getQueryParams<string>("suggestion"),
      routes.getQueryParams<string>("similarity")
    )
  );

  routes.watchBrowserNavigation(() => {
    recordCriteria.value.complete(
      routes.getQueryParams<string>("page"),
      routes.getQueryParams<RecordStatus>("status"),
      routes.getQueryParams<string>("search"),
      routes.getQueryParams<string>("metadata"),
      routes.getQueryParams<string>("sort"),
      routes.getQueryParams<string>("response"),
      routes.getQueryParams<string>("suggestion"),
      routes.getQueryParams<string>("similarity")
    );
  });

  const updateQueryParams = async () => {
    await routes.setQueryParams(
      {
        key: "page",
        value: recordCriteria.value.committed.page.urlParams,
      },
      {
        key: "status",
        value: recordCriteria.value.committed.status,
      },
      {
        key: "search",
        value: recordCriteria.value.committed.searchText.urlParams,
      },
      {
        key: "metadata",
        value: recordCriteria.value.committed.metadata.urlParams,
      },
      {
        key: "sort",
        value: recordCriteria.value.committed.sortBy.urlParams,
      },
      {
        key: "response",
        value: recordCriteria.value.committed.response.urlParams,
      },
      {
        key: "suggestion",
        value: recordCriteria.value.committed.suggestion.urlParams,
      },
      {
        key: "similarity",
        value: recordCriteria.value.committed.similaritySearch.urlParams,
      }
    );
  };

  const loadDataset = async () => {
    try {
      isLoadingDataset.value = true;
      await getDatasetUseCase.execute(datasetId);
    } catch (error) {
      handleError(error.response);

      router.push("/");
    } finally {
      isLoadingDataset.value = false;
    }
  };

  // Handle workspace URL parameter and set workspace context from dataset
  const handleWorkspaceContext = () => {
    // Check if workspace is provided in URL query parameters
    const workspaceParam = routes.getQueryParams<string>("workspace");

    if (workspaceParam && dataset.value) {
      // If workspace parameter matches dataset's workspace, ensure it's selected
      if (dataset.value.workspace === workspaceParam) {
        const currentWorkspaces = workspaceStore.get().workspaces;
        const matchingWorkspace = currentWorkspaces.find((w) => w.name === workspaceParam);

        if (matchingWorkspace && workspaceStore.get().selectedWorkspace?.id !== matchingWorkspace.id) {
          workspaceStore.saveSelectedWorkspace(matchingWorkspace);
        }
      }
    } else if (dataset.value) {
      // If no workspace parameter, set workspace context based on dataset's workspace
      const currentWorkspaces = workspaceStore.get().workspaces;
      const datasetWorkspace = currentWorkspaces.find((w) => w.id === dataset.value.workspaceId);

      if (datasetWorkspace && workspaceStore.get().selectedWorkspace?.id !== datasetWorkspace.id) {
        workspaceStore.saveSelectedWorkspace(datasetWorkspace);

        // Update URL to include workspace parameter
        routes.setQueryParams({
          key: "workspace",
          value: datasetWorkspace.name,
        });
      }
    }
  };

  // Watch for dataset changes to update workspace context
  watch(
    () => dataset.value,
    (newDataset) => {
      if (newDataset) {
        handleWorkspaceContext();
      }
    },
    { immediate: true }
  );

  onBeforeMount(() => {
    loadDataset();
  });

  return {
    isLoadingDataset,
    recordCriteria,
    dataset,
    datasetId,
    breadcrumbs,
    updateQueryParams,
    user,
    isAdminOrOwner,
  };
};
